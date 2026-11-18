import sys,struct
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from frame_state import green_region,title_signature,screen_phase


class FrameStateTests(unittest.TestCase):
    def test_green_channels_for_all_core_formats(self):
        for kind,word,expected in [(0,31<<5,255),(2,63<<5,255)]:
            data=struct.pack('<H',word)*256*384
            values=green_region((256,384,data,512,kind))
            self.assertEqual(len(values),152*26)
            self.assertEqual(set(values),{expected})
        data=bytes([7,170,22,0])*256*384
        self.assertEqual(set(green_region((256,384,data,1024,1))),{170})

    def test_title_signature_is_invariant_under_dimming(self):
        values=bytes([73,73,178,73,178]*100)
        self.assertEqual(title_signature(values),title_signature(bytes(v*3//5 for v in values)))

    def test_blank_and_wrong_geometry_are_not_results(self):
        self.assertIsNone(title_signature(bytes([80])*200))
        self.assertIsNone(screen_phase((256,384,bytes(256*384*4),1024,1)))
        self.assertEqual(green_region((512,384,b'',0,1)),b'')
