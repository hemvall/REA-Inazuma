import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from emulator_probe import png


class PngTests(unittest.TestCase):
    def test_bgra_channels_rows_and_pitch_padding(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'frame.png'
            pixels = bytes([3, 2, 1, 255, 6, 5, 4, 255, 99, 99, 99, 99,
                            9, 8, 7, 255, 12, 11, 10, 255, 99, 99, 99, 99])
            png(target, 2, 2, pixels, 12, 1)
            data = target.read_bytes()
            offset, compressed = 8, b''
            while offset < len(data):
                length = struct.unpack_from('>I', data, offset)[0]
                kind = data[offset+4:offset+8]
                body = data[offset+8:offset+8+length]
                self.assertEqual(struct.unpack_from('>I', data, offset+8+length)[0],
                                 zlib.crc32(kind+body) & 0xffffffff)
                if kind == b'IDAT':
                    compressed += body
                offset += length+12
            self.assertEqual(zlib.decompress(compressed),
                             bytes([0, 1, 2, 3, 4, 5, 6, 0, 7, 8, 9, 10, 11, 12]))
