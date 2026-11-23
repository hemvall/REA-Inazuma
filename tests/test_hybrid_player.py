import base64
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent_runtime import LocalAgent
from arena_service import Arena, validate_decision
from player_state import compact_state, text_ready


def action():
    return {'intent':'act','reason':'Continuer','frames':6,'keys':[],
            'touch':{'x':70,'y':175},'path':[]}


def duel():
    return {'phase':'playing','screen':{'name':'duel_attack','source':'measured_frame_signature',
            'actions':[{'name':'Feinte','frames':6,'keys':[],'touch':{'x':55,'y':175}},
                       {'name':'Dribble','frames':6,'keys':[],'touch':{'x':200,'y':175}}]}}


class HybridPlayerTests(unittest.TestCase):
    def test_roster_and_phase_alone_cannot_replace_vision(self):
        self.assertFalse(text_ready({'phase':'playing','home_units':[1,2,3]}))
        self.assertFalse(text_ready({'phase':'playing','tactical':{'ready_for_text':False}}))
        self.assertFalse(text_ready({'phase':'result',**{'screen':duel()['screen']}}))
        self.assertTrue(text_ready(duel()))

    def test_compact_state_drops_script_and_keeps_unknowns_and_provenance(self):
        source = {'phase':'playing','home_units':[1]*16,
                  'fixture':{'id':'irrelevant','home':3,'away':10,'lines':['long dialogue']*6},
                  'tactical':{'source':'memory','ball':None,'ready_for_text':False}}
        state = compact_state(source)
        self.assertNotIn('fixture',state)
        self.assertNotIn('home_units',state)
        self.assertIsNone(state['tactical']['ball'])
        self.assertEqual(state['teams'],{'home':3,'away':10})

    def test_text_request_has_no_image_and_only_a_named_legal_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = LocalAgent(directory)
            agent.provider.invoke = Mock(return_value='{"action":"Dribble","reason":"Passer le défenseur"}')
            result = agent.play(None,duel(),[],threading.Event())
            validate_decision(result)
            self.assertEqual(result['touch'],{'x':200,'y':175})
            request = agent.provider.invoke.call_args.args[0]
            self.assertIsNone(request.image)
            self.assertEqual(request.schema['properties']['action']['enum'], ['Feinte', 'Dribble'])
            with self.assertRaises(ValueError):
                agent.play(None,{'phase':'playing'},[],threading.Event())

    def test_text_hallucination_cannot_produce_a_touch(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = LocalAgent(directory)
            agent.generate = Mock(return_value={'action':'Sortir du jeu','reason':'x'})
            with self.assertRaises(ValueError):
                agent.play(None,duel(),[],threading.Event())

    def test_rule_route_neither_calls_model_nor_requests_image(self):
        with tempfile.TemporaryDirectory() as directory, patch('arena_service.ROOT',Path(directory)), \
                patch('arena_service.fast_decision',return_value=action()):
            arena = Arena()
            arena.agent = Mock()
            arena.checked = Mock()
            original = {'revision':1,'frame':10,'match':{'phase':'playing'}}
            result, observation = arena.choose_action(original,'test',0,10)
            self.assertEqual(result,action())
            self.assertIs(observation,original)
            arena.agent.play.assert_not_called()
            arena.checked.assert_not_called()
            self.assertEqual(arena.job['rule_actions'],1)

    def test_text_route_and_unknown_screen_fallback(self):
        for state, mode in ((duel(),'text'),({'phase':'playing'},'vision')):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory, \
                    patch('arena_service.ROOT',Path(directory)),patch('arena_service.fast_decision',return_value=None):
                arena = Arena()
                arena.agent = Mock()
                arena.agent.play.return_value = action()
                observation = {'revision':1,'frame':10,'match':state}
                arena.checked = Mock(return_value={**observation,'image':base64.b64encode(b'png').decode()})
                arena.choose_action(observation,'test',0,10)
                self.assertEqual(arena.job['decision_mode'],mode)
                if mode == 'text':
                    arena.checked.assert_not_called()
                    self.assertIsNone(arena.agent.play.call_args.args[0])
                else:
                    arena.checked.assert_called_once_with('observe',session_id='test',include_image=True)
                    self.assertEqual(arena.agent.play.call_args.args[0].read_bytes(),b'png')


if __name__ == '__main__':
    unittest.main()
