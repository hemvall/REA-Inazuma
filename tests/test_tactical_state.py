import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from tactical_state import (BALL_BASE, OWNER_TABLE, POSITION_BASE, POSITION_STRIDE,
                            RAM_BASE, RAM_SIZE, ROSTER_BASE, ROSTER_STRIDE,
                            SCALE, SIGNATURES, CLOCK_BASE, SCORE_BASE, SCORE_SIGNATURE,
                            extract_tactical_state)


def sample():
    memory = bytearray(RAM_SIZE)
    for address, signature in SIGNATURES.items():
        memory[address-RAM_BASE:address-RAM_BASE+len(signature)] = signature
    # The owner table index deliberately differs from the fixed roster record.
    for record, unit, side, slot, xy in ((5, 41, 0, 1, (307, 712)),
                                         (26, 189, 1, 9, (304, 304))):
        offset = ROSTER_BASE - RAM_BASE + record * ROSTER_STRIDE
        struct.pack_into('<H', memory, offset+0xF0, 9)
        struct.pack_into('<H', memory, offset+0x64, unit)
        struct.pack_into('<H', memory, offset+0x42, unit | (0x8000 if side else 0))
        memory[offset+0xB6:offset+0xB8] = bytes((side, slot))
        pointer = POSITION_BASE + record * POSITION_STRIDE
        struct.pack_into('<I', memory, offset+0xE8, pointer)
        struct.pack_into('<ii', memory, pointer-RAM_BASE, xy[0]*SCALE, xy[1]*SCALE)
    struct.pack_into('<ii', memory, BALL_BASE-RAM_BASE, 304*SCALE, 314*SCALE)
    struct.pack_into('<i', memory, BALL_BASE-RAM_BASE+0x48, 24)
    struct.pack_into('<I', memory, OWNER_TABLE-RAM_BASE+24*4,
                     ROSTER_BASE + 26*ROSTER_STRIDE)
    return memory


class TacticalStateTests(unittest.TestCase):
    def test_owner_uses_native_pointer_table_not_fixed_record_index(self):
        state = extract_tactical_state(sample(), 'playing')
        self.assertTrue(state['valid'])
        self.assertEqual(state['possession'], {'side': 'away', 'unit': 189,
                                              'record': 26, 'native_index': 24})
        self.assertEqual(state['ball']['y'], 314)
        self.assertEqual(len(state['positions']), 2)
        self.assertFalse(state['ready_for_text'])
        self.assertIn('world_to_touch', state['unavailable'])
        self.assertEqual(state['legal_actions'], [])

    def test_invalid_runtime_pointer_does_not_read_other_memory(self):
        memory = sample()
        struct.pack_into('<I', memory,
                         ROSTER_BASE-RAM_BASE+26*ROSTER_STRIDE+0xE8, 0xFFFFFFFF)
        state = extract_tactical_state(memory, 'playing')
        self.assertFalse(state['valid'])
        self.assertIsNone(state['ball'])

    def test_unknown_owner_keeps_possession_unknown(self):
        memory = sample()
        struct.pack_into('<i', memory, BALL_BASE-RAM_BASE+0x48, 133)
        state = extract_tactical_state(memory, 'playing')
        self.assertIsNone(state['possession'])
        self.assertFalse(state['valid'])

    def test_free_ball_is_distinct_from_unknown_owner(self):
        memory = sample()
        struct.pack_into('<i', memory, BALL_BASE-RAM_BASE+0x48, -1)
        state = extract_tactical_state(memory, 'playing')
        self.assertTrue(state['valid'])
        self.assertEqual(state['possession']['side'], 'none')

    def test_wrong_version_and_loading_never_expose_stale_positions(self):
        memory = sample()
        memory[0x62E94] ^= 1
        self.assertFalse(extract_tactical_state(memory, 'playing')['valid'])
        state = extract_tactical_state(sample(), 'loading')
        self.assertEqual(state['positions'], [])
        self.assertIsNone(state['possession'])
        self.assertFalse(extract_tactical_state(b'', 'playing')['valid'])

    def test_score_and_clock_require_their_signature_and_consistent_mirror(self):
        memory = sample()
        memory[0x6ABDC:0x6ABDC+len(SCORE_SIGNATURE)] = SCORE_SIGNATURE
        struct.pack_into('<BB',memory,SCORE_BASE-RAM_BASE,0,1)
        struct.pack_into('<II',memory,CLOCK_BASE-RAM_BASE,27672,27672)
        memory[0xCA3FF] = 1
        state = extract_tactical_state(memory,'playing')
        self.assertEqual(state['score'],{'home':0,'away':1})
        self.assertEqual(state['clock']['seconds'],922)
        self.assertEqual(state['clock']['period_raw'],1)
        struct.pack_into('<I',memory,CLOCK_BASE-RAM_BASE+4,27673)
        self.assertIsNone(extract_tactical_state(memory,'playing')['clock'])
        memory[0x6ABDC] ^= 1
        self.assertIsNone(extract_tactical_state(memory,'playing')['score'])

    @unittest.skipUnless(Path('build/research/score-clock/goal.ram').exists(), 'Local native goal fixture unavailable')
    def test_retained_native_goal_readback(self):
        memory = Path('build/research/score-clock/goal.ram').read_bytes()
        state = extract_tactical_state(memory,'playing')
        self.assertTrue(state['valid'])
        self.assertEqual(len(state['positions']),22)
        self.assertEqual(state['score'],{'home':0,'away':1})
        self.assertEqual(state['clock']['seconds'],15*60+22)
        self.assertFalse(state['ready_for_text'])


if __name__ == '__main__':
    unittest.main()
