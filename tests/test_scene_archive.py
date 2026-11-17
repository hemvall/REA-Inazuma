import struct
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from scene_archive import replace_entries
from ie2_formats import unpack_index


class AllocationTests(unittest.TestCase):
    def fixture(self):
        h = bytearray(0x30+36)
        h[:16] = b'PackNum 20080626'
        struct.pack_into('<H', h, 0x16, 3)
        for i, row in enumerate(((1,0,8),(2,8,40),(3,48,8))):
            struct.pack_into('<III', h, 0x30+12*i, *row)
        return h, bytes(range(56))

    def test_longer_entry_uses_reclaimed_tail(self):
        h, b = self.fixture()
        nh, nb, positions = replace_entries(h,b,{1:b'A'*20,2:b'B'*8})
        self.assertEqual(positions, {2:8,1:16})
        self.assertEqual(nb[16:36],b'A'*20)
        self.assertEqual(nb[8:16],b'B'*8)
        self.assertEqual(nb[48:],b[48:])
        self.assertEqual(unpack_index(nh,nb)[2],(3,48,8))

    def test_insufficient_space_fails(self):
        h,b = self.fixture()
        with self.assertRaisesRegex(ValueError,'No reclaimed'):
            replace_entries(h,b,{1:b'A'*60,2:b'B'*8})

    def test_repack_combines_neighboring_replaced_slots(self):
        h,b = self.fixture()
        nh,nb,pos = replace_entries(h,b,{1:b'A'*28,2:b'B'*20})
        self.assertEqual(pos,{1:0,2:28})
        self.assertEqual(nb[:48],b'A'*28+b'B'*20)
        self.assertEqual(nb[48:],b[48:])

    def test_unselected_entry_is_not_a_donor(self):
        h,b = self.fixture()
        with self.assertRaisesRegex(ValueError,'No reclaimed'):
            replace_entries(h,b,{1:b'A'*12,3:b'C'*4})

    def test_alignment_rejected(self):
        h,b = self.fixture()
        with self.assertRaisesRegex(ValueError,'padding'):
            replace_entries(h,b,{1:b'A'})
