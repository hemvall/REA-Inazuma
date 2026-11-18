import sys,struct
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from frame_state import green_region,title_signature,screen_phase,screen_observation


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

    def test_unknown_frame_exposes_no_controls(self):
        for frame in (None,(256,384,bytes(256*384*4),1024,1),(512,384,b'',0,1)):
            state=screen_observation(frame)
            self.assertEqual(state['name'],'unknown')
            self.assertEqual(state['actions'],[])

    @unittest.skipUnless(Path('build/research/field-0.png').is_file(), 'Requires local measured captures')
    def test_measured_screens_and_dimming(self):
        from PIL import Image
        samples={
            'formation_overview':'build/research/continue-7.png',
            'formation_details':'build/research/continue-10.png',
            'kickoff_ready':'build/research/field-0.png',
            'goal_replay':'build/research/native-screen.png',
            'stylus_prompt':'build/research/arena-play-10.png',
            'defence_duel':'build/research/field-3.png',
            'attack_duel':'build/research/native-start.png',
            'halftime':'build/delivery/halftime.png',
        }
        for expected,path in samples.items():
            if not Path(path).is_file():continue
            image=Image.open(path).convert('RGBA')
            for dim in (1,.6):
                data=bytes(int(value*dim) for value in image.tobytes())
                result=screen_observation((256,384,data,1024,1))
                with self.subTest(expected=expected,dim=dim):
                    self.assertEqual(result['name'],expected)
            # A different control label must reject the screen, not match its
            # other region alone. Erase both controls in the bottom toolbar.
            raw=bytearray(image.tobytes())
            raw[350*1024:384*1024]=bytes(34*1024)
            if expected not in ('stylus_prompt','goal_replay'):
                self.assertEqual(screen_observation((256,384,bytes(raw),1024,1))['name'],'unknown')
