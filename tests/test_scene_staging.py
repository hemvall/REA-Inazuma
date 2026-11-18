import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scene_staging import gather_raimon, begin_enemy_arrival, end_enemy_arrival
from ssd import Program, read_ssd
from ie2_formats import text_records


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(Path('story/standalone_scene.json').read_text(encoding='utf-8'))

    def test_controlled_mark_is_not_deleted_or_teleported(self):
        p = Program()
        gather_raimon(p, self.config['characters'])
        for row in p.rows:
            if row.opcode in (0x3058,0x3059,0x305A):
                self.assertNotEqual(row.args[0],1)

    def test_every_player_walks_in_staggered_native_threads(self):
        p = Program()
        gather_raimon(p, self.config['characters'])
        read_ssd(p.encode()[0])
        walks = [r for r in p.rows if r.opcode == 0x3066]
        self.assertEqual({r.args[0] for r in walks},set(self.config['team']['units']))
        self.assertEqual([r.args for r in p.rows if r.opcode == 0x6014],[[0],[5],[10],[15],[20]])
        self.assertTrue(all(r.types[-1] == 2 and r.args[-1] == 256 for r in walks))
        self.assertEqual(sum(r.opcode == 0x6013 for r in p.rows),1)

    def test_enemy_appears_between_native_white_fades(self):
        p = Program()
        begin_enemy_arrival(p)
        p.emit(0x3058,2141,0)
        end_enemy_arrival(p,self.config['characters'],2141)
        ssd,sst = p.encode()
        rows,_=read_ssd(ssd)
        self.assertEqual(text_records(sst)[0]['text'],b'2D_170')
        start = next(i for i,r in enumerate(rows) if r.opcode==0x3005)
        spawn = next(i for i,r in enumerate(rows) if r.opcode==0x3058)
        finish = next(i for i,r in enumerate(rows) if r.opcode==0x3004)
        self.assertEqual(rows[start].args,[33,5])
        self.assertEqual(rows[finish].args,[33,5])
        self.assertLess(start,spawn)
        self.assertLess(spawn,finish)
        self.assertEqual(rows[start-1].opcode,0x3015)
        self.assertEqual(rows[start-1].args,[1,770])


if __name__ == '__main__':
    unittest.main()
