"""Proposed ROM mailbox codec. No memory address or native hook is assumed.

This host-side contract is not evidence that a ROM can consume its payload.
Only a measured profile and a ROM acknowledgement may enable dynamic_match.
"""
import struct
import zlib

MAGIC = b'IZM1'
VERSION = 1
HEADER = struct.Struct('<4sHHIIII')
CONFIG = struct.Struct('<HHHH')
LINE = struct.Struct('<HH')
MAX_PAYLOAD = 4096
STATES = {'idle': 0, 'preparing': 1, 'ready': 2, 'dialogue': 3,
          'playing': 4, 'result': 5, 'error': 6}


def unsigned(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f'Expected uint{bits}')
    return value


def encode_config(home, away, match_format, lines):
    for value in (home, away, match_format):
        unsigned(value, 16)
    if home == away:
        raise ValueError('Teams must differ')
    if not isinstance(lines, list) or not 4 <= len(lines) <= 6:
        raise ValueError('Expected 4..6 dialogue lines')
    payload = bytearray(CONFIG.pack(home, away, match_format, len(lines)))
    for line in lines:
        if not isinstance(line, dict) or set(line) != {'speaker', 'text'}:
            raise ValueError('Expected speaker and text')
        speaker = unsigned(line['speaker'], 16)
        text = line['text']
        if not isinstance(text, str) or not text.strip() or any(ord(c) < 32 for c in text):
            raise ValueError('Invalid dialogue text')
        encoded = text.encode('utf-8')
        if len(encoded) > 512:
            raise ValueError('Dialogue line exceeds 512 UTF-8 bytes')
        payload.extend(LINE.pack(speaker, len(encoded)))
        payload.extend(encoded)
    if len(payload) > MAX_PAYLOAD:
        raise ValueError('Payload too large')
    return bytes(payload)


def packet(request_id, state, payload=b'', error=0):
    unsigned(request_id, 32)
    unsigned(error, 32)
    if not request_id or state not in STATES or not isinstance(payload, bytes) or len(payload) > MAX_PAYLOAD:
        raise ValueError('Invalid mailbox packet')
    return HEADER.pack(MAGIC, VERSION, STATES[state], request_id, len(payload),
                       zlib.crc32(payload), error) + payload


def read_packet(data):
    if len(data) < HEADER.size:
        raise ValueError('Truncated header')
    magic, version, state, request_id, size, checksum, error = HEADER.unpack_from(data)
    if magic != MAGIC or version != VERSION or state not in STATES.values() or not request_id:
        raise ValueError('Incompatible mailbox')
    if size > MAX_PAYLOAD or len(data) != HEADER.size + size:
        raise ValueError('Invalid payload size')
    payload = data[HEADER.size:]
    if zlib.crc32(payload) != checksum:
        raise ValueError('Payload checksum mismatch')
    return {'request_id': request_id, 'state': next(k for k, v in STATES.items() if v == state),
            'error': error, 'payload': payload}


def acknowledged(data, expected_request_id):
    result = read_packet(data)
    if result['request_id'] != expected_request_id:
        raise ValueError('Stale acknowledgement')
    if result['state'] != 'ready' or result['error']:
        raise ValueError('ROM not ready')
    return result
