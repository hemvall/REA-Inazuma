import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent_runtime import LocalAgent
from arena_service import Arena


class SemanticPilotTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch('arena_service.ROOT', self.folder))
        self.arena = Arena(stream_video=False)
        self.arena.session = Mock(session_id='match', owner='human', profile='arena')
        self.arena.session.set_control.side_effect = self.set_control
        self.arena.fixture = {'home': 3, 'away': 10}
        self.arena.agent = Mock()
        self.state = {'phase': 'playing', 'screen': 'attack_duel', 'frame': 30,
                      'revision': 2, 'clock': None, 'score': None, 'possession': None,
                      'legal_actions': [{'id': 'duel.dribble'}, {'id': 'duel.feint'}]}
        self.commands = []
        self.arena.checked = Mock(side_effect=self.checked)

    def set_control(self, session_id, owner):
        self.arena.session.owner = owner

    def checked(self, operation, **arguments):
        self.commands.append((operation, arguments))
        if operation == 'apply_match_action':
            self.state = {**self.state, 'phase': 'result', 'frame': self.state['frame'] + 10,
                          'legal_actions': []}
        elif operation == 'advance_match':
            self.state = {**self.state, 'legal_actions': [{'id': 'duel.dribble'}]}
        return {'match_observation': self.state}

    def play(self, mode='ai'):
        self.arena.delegate('match', mode=mode)
        self.wait_for_pilot()

    def wait_for_pilot(self):
        self.arena.thread.join(3)
        self.assertFalse(self.arena.thread.is_alive())
        self.assertEqual(self.arena.session.owner, 'human')
        self.assertEqual(self.arena.job['vision_calls'], 0)

    def test_model_receives_text_and_schema_from_current_observation(self):
        agent = LocalAgent(self.folder)
        agent.generate = Mock(return_value={'action_id': 'duel.feint'})
        self.arena.agent = agent
        self.play()
        (prompt, schema), options = agent.generate.call_args
        self.assertEqual(json.loads(prompt.split('\n', 1)[1])['frame'], 30)
        self.assertEqual(schema['properties']['action_id']['enum'], ['duel.dribble', 'duel.feint'])
        self.assertNotIn('image', options)
        self.assertEqual(self.arena.history, ['duel.feint'])
        self.assertEqual(self.commands[-1][1]['revision'], 2)
        self.assertEqual(self.commands[-1][1]['frame'], 30)

    def test_stale_action_is_recomputed_from_fresh_state(self):
        def checked(operation, **arguments):
            if operation == 'apply_match_action' and arguments['revision'] == 2:
                self.state = {**self.state, 'frame': 31, 'revision': 3}
                raise ValueError('Observation périmée.')
            return self.checked(operation, **arguments)

        self.arena.checked.side_effect = checked
        self.arena.agent.decide_match_action.return_value = {'action_id': 'duel.feint'}
        self.play()
        self.assertEqual(self.arena.job['rejected_commands'], 1)
        self.assertEqual(self.arena.job['text_calls'], 2)
        self.assertEqual(self.commands[-1][1]['revision'], 3)
        self.assertEqual(self.commands[-1][1]['frame'], 31)

    def test_late_response_cannot_send_command_after_handoff(self):
        deciding = threading.Event()
        release = threading.Event()

        def decide(observation, cancel):
            deciding.set()
            if not release.wait(3):
                raise TimeoutError()
            return {'action_id': 'duel.feint'}

        self.arena.agent.decide_match_action.side_effect = decide
        self.arena.delegate('match', mode='ai')
        try:
            self.assertTrue(deciding.wait(3))
            self.arena.stop('match')
        finally:
            release.set()
            self.wait_for_pilot()
        self.assertEqual(self.arena.job['state'], 'cancelled')
        self.assertEqual([operation for operation, _ in self.commands], ['playback', 'observe_match'])

    def test_advance_and_single_action_skip_model(self):
        self.state['legal_actions'] = []
        self.play()
        self.arena.agent.decide_match_action.assert_not_called()
        self.assertEqual(self.arena.history, ['duel.dribble'])

    def test_deterministic_mode_skips_model_with_multiple_actions(self):
        self.play('deterministic')
        self.arena.agent.decide_match_action.assert_not_called()
        self.assertEqual(self.arena.history, ['duel.dribble'])

    def assert_fallback(self, reason, response=None, error=None):
        self.arena.agent.decide_match_action.return_value = response
        self.arena.agent.decide_match_action.side_effect = error
        self.play()
        self.assertEqual(self.arena.history, ['duel.dribble'])
        self.assertEqual(self.arena.job['fallback_count'], 1)
        journal = self.folder / 'build/agents' / f"{self.arena.job['id']}-match.jsonl"
        decisions = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]
        self.assertEqual([row['fallback'] for row in decisions if row['event'] == 'decision'], [reason])

    def test_illegal_action(self):
        self.assert_fallback('invalid_response', {'action_id': 'duel.unknown'})

    def test_invalid_format(self):
        self.assert_fallback('invalid_response', ['duel.feint'])

    def test_model_unavailable(self):
        self.assert_fallback('model_unavailable', error=ConnectionRefusedError())

    def test_model_timeout(self):
        self.assert_fallback('timeout', error=TimeoutError())
