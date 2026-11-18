import unittest
from types import SimpleNamespace
from emulator_worker import Controller,execute_step


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.samples = []
        self.emulator = SimpleNamespace(frames=0, touch=None, pressed=set())
        self.emulator.lib = SimpleNamespace(
            retro_run=lambda: self.samples.append(self.emulator.touch))
        self.controller = Controller(self.emulator)

    def test_continuous_path_and_release(self):
        result = self.controller.touch_path(0, [
            {'x': 10, 'y': 20, 'frames': 2},
            {'x': 30, 'y': 40, 'frames': 1}])
        self.assertEqual(self.samples, [(10, 20), (10, 20), (30, 40), None, None, None, None])
        self.assertIsNone(self.emulator.touch)
        self.assertEqual(result, {'revision': 1, 'frame': 7})

    def test_invalid_tail_has_no_effect(self):
        with self.assertRaises(ValueError):
            self.controller.touch_path(0, [
                {'x': 10, 'y': 20, 'frames': 1},
                {'x': 256, 'y': 20, 'frames': 1}])
        self.assertEqual(self.samples, [])

    def test_stale_revision(self):
        with self.assertRaises(ValueError):
            self.controller.touch_path(1, [{'x': 0, 'y': 0, 'frames': 1}])
        self.assertEqual(self.samples, [])

    def test_step_freezes_on_final_frame_without_releasing_into_native_exit(self):
        advanced=execute_step(self.emulator,120,['B'],None,lambda:len(self.samples)>=2)
        self.assertEqual(advanced,2)
        self.assertEqual(len(self.samples),2)
        self.assertEqual(self.emulator.pressed,set())

    def test_already_finished_screen_never_advances_native_core(self):
        self.assertEqual(execute_step(self.emulator,120,['B'],None,lambda:True),0)
        self.assertEqual(self.samples,[])

    def test_stroke_stops_at_result_without_native_release_frames(self):
        controller=Controller(self.emulator,lambda:len(self.samples)>=2)
        result=controller.touch_path(0,[{'x':10,'y':20,'frames':10}])
        self.assertEqual(result['frame'],2)
        self.assertEqual(self.samples,[(10,20),(10,20)])

    def test_held_input_has_no_artificial_release_gap(self):
        keys=[]
        self.emulator.lib.retro_run=lambda:keys.append(set(self.emulator.pressed))
        execute_step(self.emulator,6,['UP'],None,release=False)
        execute_step(self.emulator,6,['UP'],None,release=False)
        self.assertEqual(len(keys),12)
        self.assertTrue(all(sample for sample in keys))
        execute_step(self.emulator,1,[],None,release=False)
        self.assertEqual(keys[-1],set())

    def test_held_stylus_preserves_position_and_result_guard(self):
        count=execute_step(self.emulator,6,[],[100,120],lambda:len(self.samples)>=3,release=False)
        self.assertEqual(count,3)
        self.assertEqual(self.samples,[[100,120]]*3)
        self.assertIsNone(self.emulator.touch)
