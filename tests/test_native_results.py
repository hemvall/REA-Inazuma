import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nds import read_rom
from prepare_scene import prepare
from ie2_formats import unpack_index, decompress_lz10
from ssd import read_ssd


@unittest.skipUnless(Path('rom/original.nds').exists(), 'Requires the user-supplied ROM')
class NativeResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom=read_rom('rom/original.nds')
        config=json.loads(Path('story/standalone_scene.json').read_text(encoding='utf-8'))
        cls.manifest,_=prepare(cls.rom,config)

    def test_native_match_result_and_text_archives_are_not_patched(self):
        self.assertFalse(any('/mch.' in e['path'] or '/mcht.' in e['path']
                             for e in self.manifest['edits']))

    def test_result_display_precedes_teardown_in_the_original_challenge(self):
        base='data_iz/script/fr/mch'
        header=self.rom.data[slice(*self.rom.files[base+'.pkh'])]
        blob=self.rom.data[slice(*self.rom.files[base+'.pkb'])]
        _,pos,size=next(r for r in unpack_index(header,blob) if r[0]==24010035)
        rows,_=read_ssd(decompress_lz10(blob[pos:pos+size])[0])
        def body(ident):
            start=next(i for i,r in enumerate(rows) if r.opcode==0x3001 and r.args[1]==ident)
            stop=next((i for i in range(start+1,len(rows)) if rows[i].opcode==0x3001),len(rows))
            return rows[start+1:stop]
        self.assertTrue(any(r.opcode==0x2010 for r in body(0x1005)))
        self.assertFalse(any(r.opcode in (0x200F,0x4016) for r in body(0x1005)))
        self.assertTrue(any(r.opcode==0x6013 for r in body(0x2010)))
        self.assertTrue(any(r.opcode==0x200F for r in body(0x1004)))


if __name__=='__main__':
    unittest.main()
