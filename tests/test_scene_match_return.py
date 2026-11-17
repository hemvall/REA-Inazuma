from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nds import read_rom
from ie2_formats import unpack_index, decompress_lz10
from scene_match_return import prepare_match_return, BASE, KEY
from ssd import read_ssd


@unittest.skipUnless(Path('rom/original.nds').exists(), 'Requires the user-supplied ROM')
class MatchReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rom = read_rom('rom/original.nds')
        edits, _ = prepare_match_return(rom)
        cls.before = {BASE+stem+s: rom.data[slice(*rom.files[BASE+stem+s])]
                      for stem in ('mch','mcht') for s in ('.pkh','.pkb')}
        cls.after = {p: bytearray(b) for p,b in cls.before.items()}
        for edit in edits:
            b = bytes.fromhex(edit['after_hex'])
            cls.after[edit['path']][edit['offset']:edit['offset']+len(b)] = b

    def rows(self, parts):
        header, blob = parts[BASE+'mch.pkh'], parts[BASE+'mch.pkb']
        _, pos, size = next(r for r in unpack_index(header, blob) if r[0] == KEY)
        return read_ssd(decompress_lz10(blob[pos:pos+size])[0])[0]

    def test_other_matches_are_unchanged(self):
        a = unpack_index(self.before[BASE+'mch.pkh'], self.before[BASE+'mch.pkb'])
        b = unpack_index(self.after[BASE+'mch.pkh'], self.after[BASE+'mch.pkb'])
        self.assertEqual(len(a), len(b))
        for old, new in zip(a,b):
            if old[0] != KEY:
                self.assertEqual(old, new)
                _, pos, size = old
                self.assertEqual(self.before[BASE+'mch.pkb'][pos:pos+size],
                                 self.after[BASE+'mch.pkb'][pos:pos+size])

    def test_native_result_detection_and_slot_teardown_survive(self):
        def function(rows, ident):
            start = next(i for i,r in enumerate(rows) if r.opcode == 0x3001 and r.args[1] == ident)
            end = next((i for i in range(start+1,len(rows)) if rows[i].opcode == 0x3001),len(rows))
            return b''.join(r.encode() for r in rows[start:end])
        before, after = self.rows(self.before), self.rows(self.after)
        for ident in (0x200C, 0x200F):
            self.assertEqual(function(before,ident),function(after,ident))
        start = next(i for i,r in enumerate(after) if r.opcode == 0x3001 and r.args[1] == 0x2010)
        self.assertEqual([(r.opcode,r.args) for r in after[start+2:start+9]],
                         [(0x2011,[b]) for b in (8,16,32,512,1024,2048)]+[(0x200F,[])])


if __name__ == '__main__':
    unittest.main()
