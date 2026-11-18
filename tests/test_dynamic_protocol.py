import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from dynamic_protocol import packet, read_packet, acknowledged, encode_config


class ProtocolTests(unittest.TestCase):
    def test_corruption_and_truncation(self):
        encoded = packet(12, 'preparing', b'fixture')
        for damaged in (encoded[:-1], encoded + b'x', encoded[:-1] + b'x', b''):
            with self.assertRaises(ValueError):
                read_packet(damaged)

    def test_acknowledgement_requires_request_and_ready(self):
        self.assertEqual(acknowledged(packet(12, 'ready'), 12)['state'], 'ready')
        for encoded in (packet(11, 'ready'), packet(12, 'preparing'), packet(12, 'ready', error=1)):
            with self.assertRaises(ValueError):
                acknowledged(encoded, 12)

    def test_config_constraints(self):
        lines = [{'speaker': 1, 'text': 'Prêt pour le match ?'}] * 4
        self.assertTrue(encode_config(1, 2, 0, lines))
        for values in ((1, 1, 0, lines), (1, 2, 0, lines[:3]), (-1, 2, 0, lines)):
            with self.assertRaises(ValueError):
                encode_config(*values)
