"""Synthetic fixtures only; no Nintendo code or assets."""
import copy
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nds import Rom, crc16, patch, sha
from validate_patch import validate


def fixture():
    data = bytearray(1024)
    data[:12] = b'SYNTHETIC   '
    data[12:16] = b'TEST'
    name = b'evet.pkb'
    fnt = struct.pack('<IHH', 8, 0, 1) + bytes([len(name)]) + name + b'\0'
    struct.pack_into('<4I', data, 0x40, 0x200, len(fnt), 0x240, 8)
    data[0x200:0x200 + len(fnt)] = fnt
    struct.pack_into('<II', data, 0x240, 0x300, 0x310)
    data[0x300:0x310] = b'ORIGINAL TEXT!!!'
    struct.pack_into('<H', data, 0x15E, crc16(data[:0x15E]))
    return bytes(data)


class ToolingTests(unittest.TestCase):
    def setUp(self):
        self.rom = Rom(fixture())
        self.manifest = {'rom_sha256': sha(self.rom.data), 'edits': [{
            'path': 'evet.pkb', 'resource_sha256': sha(self.rom.data[0x300:0x310]),
            'offset': 0, 'before_hex': b'ORIGINAL'.hex(), 'after_hex': b'RAIMON!!'.hex()}]}

    def test_inspection(self):
        self.assertEqual(self.rom.files, {'evet.pkb': (0x300, 0x310)})
        self.assertEqual(self.rom.report()['game_code'], 'TEST')

    def test_patch_and_reverse(self):
        result = patch(self.rom, self.manifest)
        self.assertEqual(result[0x300:0x308], b'RAIMON!!')
        self.assertTrue(validate(self.rom, result, self.manifest)['reverse_verified'])
        self.assertEqual(self.rom.data, fixture())

    def test_wrong_rom_hash(self):
        self.manifest['rom_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            patch(self.rom, self.manifest)

    def test_wrong_resource_hash(self):
        self.manifest['edits'][0]['resource_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            patch(self.rom, self.manifest)

    def test_invalid_edits(self):
        for change in ({'offset': -1}, {'offset': 16}, {'after_hex': '00'},
                       {'before_hex': '00' * 8}, {'path': 'absent'}):
            manifest = copy.deepcopy(self.manifest)
            manifest['edits'][0].update(change)
            with self.subTest(change=change), self.assertRaises((ValueError, KeyError)):
                patch(self.rom, manifest)

    def test_overlap(self):
        self.manifest['edits'] *= 2
        with self.assertRaises(ValueError):
            patch(self.rom, self.manifest)

    def test_unexpected_output(self):
        result = bytearray(patch(self.rom, self.manifest))
        result[-1] ^= 1
        with self.assertRaises(ValueError):
            validate(self.rom, result, self.manifest)

    def test_bad_header(self):
        data = bytearray(fixture())
        data[12] ^= 1
        with self.assertRaises(ValueError):
            Rom(data)

    def test_bad_fat(self):
        data = bytearray(fixture())
        struct.pack_into('<II', data, 0x240, 0x300, 0xFFFF)
        with self.assertRaises(ValueError):
            Rom(data)

    def test_cycle(self):
        data = bytearray(fixture())
        data[0x208:0x20D] = b'\x81x\x00\xf0\x00'
        with self.assertRaises(ValueError):
            Rom(data)


if __name__ == '__main__':
    unittest.main()
