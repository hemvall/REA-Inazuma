import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from arena_service import validate_decision


class AgentActionTests(unittest.TestCase):
    def action(self):
        return {'intent':'act','reason':'Passe','frames':3,'keys':[],
                'touch':{'x':128,'y':80},'path':[]}

    def test_valid_touch(self):
        validate_decision(self.action())

    def test_rejects_unbounded_or_outside_inputs(self):
        for key,value in [('frames',121),('frames',True),('keys',['DELETE']),
                          ('touch',{'x':0,'y':192}),('touch',{'x':False,'y':1}),
                          ('intent','write_memory')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                validate_decision({**self.action(),key:value})

    def test_rejects_path_over_total_budget(self):
        with self.assertRaises(ValueError):
            validate_decision({**self.action(),'path':[{'x':1,'y':1,'frames':80}]*2})
