import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nds import read_rom
from scene_opponents import prepare_opponents


@unittest.skipUnless(Path('rom/original.nds').exists(), 'Requires the user-supplied ROM')
class OpponentIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = read_rom('rom/original.nds')
        cls.config = json.loads(Path('story/standalone_scene.json').read_text(encoding='utf-8'))

    def test_named_native_lineup_and_only_selected_team_changed(self):
        edits, evidence = prepare_opponents(self.rom, self.config)
        self.assertEqual(len(edits), 1)
        edit = edits[0]
        before, after = bytes.fromhex(edit['before_hex']), bytes.fromhex(edit['after_hex'])
        self.assertEqual(after[:32].split(b'\0')[0], b'Paradoxe FC')
        self.assertEqual([struct.unpack_from('<H', after, 64+i*8)[0] for i in range(4)],
                         [2141, 21, 2221, 2470])
        self.assertEqual(after[32:64], before[32:64])
        self.assertEqual(after[96:], before[96:])
        self.assertEqual(evidence['team_key'], 70)

    def test_wrong_identity_is_rejected(self):
        config = json.loads(json.dumps(self.config))
        config['opponents']['players'][0]['full_name'] = 'Anonymous stranger'
        with self.assertRaisesRegex(ValueError, 'identity'):
            prepare_opponents(self.rom, config)

    def test_duplicate_players_are_rejected(self):
        config = json.loads(json.dumps(self.config))
        config['opponents']['players'][1] = config['opponents']['players'][0]
        with self.assertRaisesRegex(ValueError, 'distinct'):
            prepare_opponents(self.rom, config)


if __name__ == '__main__':
    unittest.main()
