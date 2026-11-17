"""Check the native melonDS pointer conversion at screen edges."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from emulator_probe import pointer_coordinates


class PointerTests(unittest.TestCase):
    def test_native_conversion_reaches_every_pixel(self):
        for x in range(256):
            for y in (0, 1, 95, 190, 191):
                px, py = pointer_coordinates(x, y)
                # Inverse used by melonDS input.cpp, Top/Bottom, gap zero.
                self.assertEqual((px + 32768) * 256 // 65536, x)
                self.assertEqual((py + 32768) * 384 // 65536 - 192, y)

    def test_invalid_coordinates(self):
        for point in ((-1, 0), (256, 0), (0, -1), (0, 192), (1.5, 2), (True, 0)):
            with self.subTest(point=point), self.assertRaises(ValueError):
                pointer_coordinates(*point)
