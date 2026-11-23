import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fast_policy import fast_decision
from arena_service import validate_decision


class FastPolicyTests(unittest.TestCase):
    def state(self, name='kickoff_ready'):
        return {'screen':{'name':name,'source':'measured_frame_signature',
                         'actions':[{'name':'Début','frames':6,'keys':[],
                                     'touch':{'x':70,'y':175}}]}}

    def test_known_button_uses_normal_controller_schema(self):
        decision=fast_decision(self.state(),[])
        validate_decision(decision)
        self.assertEqual(decision['touch'],{'x':70,'y':175})

    def test_tactics_unknown_and_untrusted_sources_fall_back(self):
        for name in ('defence_duel','attack_duel','unknown','result'):
            self.assertIsNone(fast_decision(self.state(name),[]))
        state=self.state()
        state['screen']['source']='model_guess'
        self.assertIsNone(fast_decision(state,[]))

    def test_repeated_failed_click_is_bounded(self):
        decision=fast_decision(self.state(),[])
        self.assertIsNotNone(fast_decision(self.state(),[decision]*2))
        self.assertIsNone(fast_decision(self.state(),[decision]*3))
        self.assertIsNotNone(fast_decision(self.state(),[decision,decision,{**decision,'touch':None}]))

    def test_native_loading_wait_is_bounded_and_does_not_guess_gameplay(self):
        state = {'phase':'playing','screen':{'name':'unknown'},
                 'tactical':{'source':'native_memory','reason':'Native football roster is incomplete'}}
        decision = fast_decision(state,[])
        validate_decision(decision)
        self.assertEqual((decision['frames'],decision['keys'],decision['touch']),(120,[],None))
        self.assertIsNone(fast_decision(state,[decision]*3))
        state['tactical']['reason'] = 'Native ball owner did not resolve to an active player'
        self.assertIsNone(fast_decision(state,[]))


if __name__=='__main__':
    unittest.main()
