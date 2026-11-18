import sys
from pathlib import Path
import unittest
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena_service import Arena


class ArenaTests(unittest.TestCase):
    def setUp(self):
        self.arena = Arena()

    def test_requested_fixture_runs_organiser_then_prepares(self):
        self.arena.agent.organise=Mock(return_value={'home':3,'away':10,'lines':['test']*6})
        self.arena.list_teams=Mock(return_value=[{'id':3},{'id':10}])
        self.arena.prepare=Mock()
        result = self.arena.chat('Occulte contre Zeus')
        self.arena.thread.join(2)
        self.assertIn('job',result)
        self.arena.prepare.assert_called_once_with(3,10,['test']*6)
        self.assertEqual(self.arena.job['state'],'complete')

    def test_reverse_fixture(self):
        self.arena.agent.organise=Mock(return_value={'home':10,'away':3,'lines':['test']*6})
        self.arena.list_teams=Mock(return_value=[{'id':3},{'id':10}])
        self.arena.prepare=Mock()
        self.arena.chat('Zeus vs Occulte')
        self.arena.thread.join(2)
        self.arena.prepare.assert_called_once_with(10,3,['test']*6)

    def test_unknown_command(self):
        with self.assertRaises(ValueError):
            self.arena.call('write_memory', {})

    def test_invalid_message(self):
        for value in ('', ' ' * 4, 'a' * 2001, None):
            with self.assertRaises(ValueError):
                self.arena.chat(value)

    def test_unknown_session(self):
        with self.assertRaises(ValueError):
            self.arena.call('observe', {'session_id': 'missing'})

    def test_untrusted_organiser_team_is_rejected_before_emulation(self):
        self.arena.agent.organise=Mock(return_value={'home':999,'away':3,'lines':['test']*6})
        self.arena.list_teams=Mock(return_value=[{'id':3},{'id':10}])
        self.arena.prepare=Mock()
        self.arena.chat('Une affiche invalide')
        self.arena.thread.join(2)
        self.assertEqual(self.arena.job['state'],'error')
        self.arena.prepare.assert_not_called()

    def test_clarification_does_not_open_emulator(self):
        self.arena.agent.organise=Mock(return_value={'home':None,'away':None,'lines':[],'message':'Quelle équipe adverse ?'})
        self.arena.list_teams=Mock(return_value=[])
        self.arena.prepare=Mock()
        self.arena.chat('Zeus')
        self.arena.thread.join(2)
        self.assertEqual(self.arena.job['message'],'Quelle équipe adverse ?')
        self.arena.prepare.assert_not_called()
