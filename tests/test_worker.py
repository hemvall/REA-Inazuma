import unittest
from types import SimpleNamespace
from emulator_worker import Controller


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
