import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from native_club_scene import route_data,ram_variable,GLOBAL_BASE


class NativeRouteTests(unittest.TestCase):
    def test_two_independent_encounters_with_native_empty_records(self):
        original=bytearray(34*72)
        sentinel=struct.pack('<2H',65535,255)+bytes(68)
        original[-72:]=sentinel
        data=route_data(original)
        self.assertEqual(len(data),len(original))
        self.assertEqual(struct.unpack_from('<4H',data,62),(1,2,65535,65535))
        for index,title,game,badge in ((1,'Occulte vs Zeus',500,513),
                                     (2,'Royal Academy vs Raimon',501,549)):
            row=data[index*72:(index+1)*72]
            self.assertEqual(struct.unpack_from('<2H',row),(1,256+index))
            self.assertEqual(row[12:38].split(b'\0')[0].decode(),title)
            self.assertEqual(struct.unpack_from('<H',row,10)[0],badge)
            self.assertEqual(struct.unpack_from('<6H',row,60),(game,0,65535,65535,65535,0))
        self.assertEqual(data[216:],sentinel*31)

    def test_rejects_unknown_layout_and_out_of_bank_writes(self):
        with self.assertRaises(ValueError):route_data(bytes(72))
        for address in (GLOBAL_BASE-4,GLOBAL_BASE+1,GLOBAL_BASE+0x40000):
            with self.assertRaises(ValueError):ram_variable(address)


if __name__=='__main__':unittest.main()
