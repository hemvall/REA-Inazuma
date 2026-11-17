"""Integration checks against the user's supported ROM; no ROM is distributed."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nds import read_rom
from ie2_formats import unpack_index, decompress_lz10, text_records
from ssd import read_ssd
from scene_exploration import exploration_chapter


@unittest.skipUnless(Path('rom/original.nds').exists(), 'Requires the user-supplied ROM')
class ExplorationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rom = read_rom('rom/original.nds')
        pair = []
        for stem in ('eve', 'evet'):
            base = 'data_iz/script/fr/' + stem
            header = rom.data[slice(*rom.files[base+'.pkh'])]
            blob = rom.data[slice(*rom.files[base+'.pkb'])]
            _, offset, size = next(r for r in unpack_index(header, blob) if r[0] == 21010000)
            pair.append(decompress_lz10(blob[offset:offset+size])[0])
        cls.original, _ = read_ssd(pair[0])
        cls.config = json.loads(Path('story/standalone_scene.json').read_text(encoding='utf-8'))
        ssd, sst = exploration_chapter(*pair, cls.config)
        cls.rows, _ = read_ssd(ssd)
        cls.texts = text_records(sst)

    def test_native_return_queue_and_map_loader_survive(self):
        self.assertEqual(self.rows[166].encode(), self.original[166].encode())
        load = self.rows[2662]
        self.assertEqual(load.opcode, 0x4019)
        self.assertEqual(self.texts[load.args[0]]['text'], b'mr07b05')

    def test_only_item_and_pending_aftermath_request_the_scene(self):
        callback = None
        requests = []
        for row in self.rows:
            if row.opcode == 0x3001:
                callback = row.args[1]
            if callback < 0x2000 and row.opcode in (0x2010, 0x200F):
                requests.append((callback, row.args))
        self.assertEqual(requests, [(0x1017, [self.config['entry_key']]),
                                    (0x1014, [self.config['entry_key']])])

    def test_interaction_is_restricted_to_map_actor_and_group(self):
        declaration = next(r for r in reversed(self.rows) if r.opcode == 0x3001)
        guard = self.rows[declaration.id]
        conjunction = self.rows[guard.args[0]-1]
        predicates = [self.rows[i-1] for i in conjunction.args]
        self.assertEqual(conjunction.opcode, 0x700F)
        self.assertEqual([p.opcode for p in predicates], [0x7011, 0x7003, 0x7003])
        self.assertEqual(self.texts[predicates[0].args[1]]['text'], b'mr07b05')
        self.assertEqual([p.args[1] for p in predicates[1:]], [2004, 28])
        self.assertEqual([self.rows[p.args[0]-1].opcode for p in predicates],
                         [0x4027, 0x4015, 0x405F])


if __name__ == '__main__':
    unittest.main()
