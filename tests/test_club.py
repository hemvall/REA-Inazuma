import ctypes as C
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from club_bridge import ClubBridge
from club_fixtures import FIXTURES
from arena_service import Arena
from club_scene import event_pair
from ssd import read_ssd


class ClubSelectionTests(unittest.TestCase):
    def setUp(self):
        self.ram = C.create_string_buffer(4*1024*1024)
        self.bridge = ClubBridge.__new__(ClubBridge)
        self.bridge.emulator = Mock(last_frame=None)
        self.bridge.emulator.lib.retro_get_memory_data.return_value = C.addressof(self.ram)
        self.bridge.profile = {'global_base':0x020DBEBC}
        self.bridge.fixture = None
        self.bridge.completed = self.bridge.preparing = False
        self.bridge.prepare = Mock()

    def mailbox(self, flag=10500, counter=4, selection=1):
        base = 0xDBEBC
        for index, value in ((5,flag),(8,counter),(15,selection)):
            struct.pack_into('<I', self.ram, base+4*index, value)

    def test_native_offers_prepare_actual_teams_then_acknowledge(self):
        for selected, (home,away,_) in FIXTURES.items():
            self.mailbox(selection=selected)
            self.bridge.poll_frame()
            args = self.bridge.prepare.call_args.args
            self.assertEqual(args[:2], (home,away))
            self.assertEqual(len(args[2]), 6)
            self.assertEqual(struct.unpack_from('<I',self.ram,0xDBEBC+60)[0],0)

    def test_invalid_request_has_no_effect(self):
        self.mailbox(selection=999)
        before = self.ram.raw
        with self.assertRaises(ValueError): self.bridge.poll_frame()
        self.bridge.prepare.assert_not_called()
        self.assertEqual(self.ram.raw,before)

    def test_cancel_and_wrong_scene_do_not_prepare(self):
        for flag,counter in ((10500,0),(10500,20),(10100,4)):
            self.mailbox(flag=flag,counter=counter)
            self.bridge.poll_frame()
        self.bridge.prepare.assert_not_called()

    def test_failed_preparation_is_not_acknowledged(self):
        self.mailbox()
        self.bridge.prepare.side_effect = ValueError('unavailable native buffer')
        with self.assertRaises(ValueError): self.bridge.poll_frame()
        self.assertEqual(struct.unpack_from('<I',self.ram,0xDBEBC+60)[0],1)
        self.assertFalse(self.bridge.preparing)

    def test_club_service_uses_same_worker_without_agent(self):
        arena = Arena()
        arena.session.open = Mock(return_value={'session_id':'club'})
        arena.checked = Mock()
        arena.agent.organise = Mock()
        arena.call('open_club', {})
        arena.thread.join(2)
        arena.session.open.assert_called_once_with('club', cancel=arena.cancel)
        arena.checked.assert_called_once_with('observe',session_id='club')
        arena.agent.organise.assert_not_called()
        self.assertEqual(arena.job['state'],'complete')

    def test_opening_club_does_not_replace_active_match(self):
        arena = Arena()
        arena.session.session_id = 'existing'
        arena.session.open = Mock()
        with self.assertRaises(ValueError): arena.call('open_club', {})
        arena.session.open.assert_not_called()


@unittest.skipUnless(Path('rom/original.nds').is_file(), 'Requires user-supplied ROM')
class NativeClubScriptTests(unittest.TestCase):
    def test_choice_messages_leave_input_to_the_native_selector(self):
        import json
        from prepare_arena import scene_pair
        from nds import read_rom
        config=json.loads(Path('story/standalone_scene.json').read_text())
        ssd,_=event_pair(*scene_pair(read_rom('rom/original.nds')),config)
        rows,_=read_ssd(ssd)
        choices=[i for i,row in enumerate(rows) if row.opcode==0x3057]
        self.assertEqual(len(choices),len(FIXTURES)+1)
        for i in choices:
            self.assertEqual(rows[i-1].opcode,0x301D)
            self.assertEqual(rows[i-1].unknown,0)
            self.assertEqual(rows[i+1].opcode,0x6008)
            self.assertEqual(rows[i+2].opcode,0x4020)
