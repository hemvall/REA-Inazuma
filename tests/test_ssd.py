"""Synthetic tests for SSD block references, expressions and SST bindings."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ssd import Program, expression, variable, string, fixed, read_ssd, helper_prefix
from ie2_formats import text_records


class ScriptTests(unittest.TestCase):
    def test_function_pairing_and_text_binding(self):
        program = Program()
        opened = program.function(0x1023)
        say = program.emit(0x301D, string('Raimon !', 1, 1))
        program.end(opened)
        binary, text = program.encode()
        rows, header = read_ssd(binary)
        self.assertEqual(rows[1].args, [0, 4])
        self.assertEqual(rows[-1].args, [0, 2])
        self.assertEqual(header['text_count'], 1)
        self.assertEqual(text_records(text)[0]['command'], say.id)
        self.assertEqual(b''.join(r.encode() for r in rows), binary[32:])
        self.assertEqual(struct.unpack_from('<I', binary, 8)[0], len(binary)+len(text)-4)

    def test_nested_expression_ids_are_one_based(self):
        program = Program()
        block = program.function(0x1013, expression(0x7003, variable(0x10009), 1))
        program.emit(0x3059, expression(0x4045, 0), 0)
        program.end(block)
        rows, _ = read_ssd(program.encode()[0])
        self.assertEqual(rows[1].args, [3])
        self.assertEqual(rows[2].opcode, 0x7003)
        self.assertEqual(rows[4].args[0], rows[5].id)

    def test_helper_strip_preserves_prefix(self):
        program = Program()
        block = program.function(0x2000)
        program.emit(0x3008, 0, string('ie0103'))
        program.end(block)
        shared_count = len(program.rows)
        block = program.function(0x1023)
        program.emit(0x301D, string('old scene', 1, 1))
        program.end(block)
        rows, texts, header = helper_prefix(*program.encode())
        self.assertEqual(len(rows), shared_count)
        self.assertEqual(len(texts), 1)
        new = Program(rows, texts, header)
        block = new.function(0x1017)
        new.emit(0x301D, string('new scene', 1, 1))
        new.end(block)
        _, sst = new.encode()
        self.assertNotIn(b'old scene', sst)
        self.assertIn(b'new scene', sst)

    def test_fixed_point(self):
        self.assertEqual(fixed(90), (2, 368640))
        self.assertEqual(fixed(-1.5), (2, -6144))

    def test_nested_result_block_pairing(self):
        program = Program()
        function = program.function(0x1013)
        program.emit(0x6008, expression(0x7003, variable(0x10009), 1))
        branch = program.emit(0x6001, 1, 0)
        program.emit(0x301D, string('Bravo !', 1, 1))
        program.end(branch)
        program.end(function)
        rows, _ = read_ssd(program.encode()[0])
        self.assertEqual(rows[-2].args, [1, branch.id])
        self.assertEqual(rows[-1].args, [0, function.id])

    def test_invalid_header_rejected(self):
        with self.assertRaises(ValueError):
            read_ssd(b'SSD\0'+bytes(28))

    def test_bad_reference_rejected(self):
        program = Program()
        block = program.function(0x1023)
        program.end(block)
        block.args[1] = 999
        with self.assertRaises(ValueError):
            program.encode()


if __name__ == '__main__':
    unittest.main()
