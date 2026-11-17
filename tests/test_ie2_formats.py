"""Asset-free tests for the archive and compression primitives."""
import random
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ie2_formats import compress_lz10, compress_lz10_padded, decompress_lz10, text_records, unpack_index


class FormatTests(unittest.TestCase):
    def test_archive_word_padding(self):
        for data in (b'A', b'ABC', b'Raimon'*30):
            encoded = compress_lz10_padded(data)
            decoded, used = decompress_lz10(encoded)
            self.assertEqual(decoded, data)
            self.assertEqual(len(encoded) % 4, 0)
            self.assertLessEqual(len(encoded)-used, 3)
            self.assertEqual(encoded[used:], bytes(len(encoded)-used))

    def test_lz_literal_fixture(self):
        self.assertEqual(decompress_lz10(b'\x10\x03\0\0\0ABC'), (b'ABC', 8))

    def test_lz_overlap_fixture(self):
        self.assertEqual(decompress_lz10(b'\x10\x07\0\0\x40A\x30\0')[0], b'AAAAAAA')

    def test_round_trips(self):
        rng = random.Random(17)
        for data in [b'A', b'A'*80, b'Raimon'*100, rng.randbytes(6000),
                     rng.randbytes(4096)*2, b'abcd'*1000+b'abc']:
            with self.subTest(size=len(data)):
                self.assertEqual(decompress_lz10(compress_lz10(data))[0], data)

    def test_bad_reference(self):
        with self.assertRaises(ValueError):
            decompress_lz10(b'\x10\x03\0\0\x80\0\0')

    def test_text_records(self):
        record = struct.pack('<4H', 751, 1, 16, 13) + b'HELLO\0\0\0'
        parsed = text_records(struct.pack('<I', len(record)) + record)
        self.assertEqual(parsed[0]['text'], b'HELLO')
        self.assertEqual(parsed[0]['command'], 751)
        with self.assertRaises(ValueError):
            text_records(b'\0'*8)

    def test_archive_index(self):
        header = bytearray(64)
        header[:16] = b'PackNum 20080626'
        struct.pack_into('<H', header, 0x16, 1)
        struct.pack_into('<III', header, 0x30, 123, 0, 8)
        self.assertEqual(unpack_index(header, b'12345678'), [(123, 0, 8)])
        with self.assertRaises(ValueError):
            unpack_index(header, b'1234')


if __name__ == '__main__':
    unittest.main()
