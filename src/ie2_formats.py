"""Measured IE2 PackNum archive and Nintendo LZ10 primitives.

PKH layout cross-checked against Tinke's public format reader, then against
the supplied BEBF revision 0 archive. No game assets are embedded here.
"""
import struct


def unpack_index(header, blob):
    if header[:16] != b'PackNum 20080626':
        raise ValueError('Unsupported PKH signature')
    kind = struct.unpack_from('<H', header, 0x12)[0]
    count = struct.unpack_from('<H', header, 0x16)[0]
    if kind != 0 or 0x30 + count * 12 > len(header):
        raise ValueError('Unsupported PKH table')
    result = []
    for i in range(count):
        key, offset, size = struct.unpack_from('<III', header, 0x30 + 12*i)
        if offset + size > len(blob):
            raise ValueError('PKH entry outside PKB')
        result.append((key, offset, size))
    return result


def decompress_lz10(data):
    if len(data) < 4 or data[0] != 0x10:
        raise ValueError('Not an LZ10 stream')
    size = int.from_bytes(data[1:4], 'little')
    if size == 0 or size > 16*1024*1024:
        raise ValueError('Unsupported decoded size')
    output = bytearray()
    pos = 4
    while len(output) < size:
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(output) == size:
                break
            if flags & (1 << bit):
                a, b = data[pos:pos+2]
                pos += 2
                length = (a >> 4) + 3
                distance = ((a & 15) << 8 | b) + 1
                if distance > len(output) or len(output) + length > size:
                    raise ValueError('Invalid LZ10 reference')
                for _ in range(length):
                    output.append(output[-distance])
            else:
                output.append(data[pos])
                pos += 1
    return bytes(output), pos


def compress_lz10(data):
    """Deterministic greedy LZ10 encoder with the standard 4 KiB window."""
    if not 0 < len(data) < 0x1000000:
        raise ValueError('Unsupported LZ10 size')
    out = bytearray(b'\x10' + len(data).to_bytes(3, 'little'))
    pos = 0
    while pos < len(data):
        flag_pos = len(out)
        out.append(0)
        for bit in range(7, -1, -1):
            if pos == len(data):
                break
            best_length = 0
            best_distance = 0
            for length in range(min(18, len(data)-pos), 2, -1):
                index = data.rfind(data[pos:pos+length], max(0, pos-4096), pos+length-1)
                if index != -1 and index < pos:
                    best_length, best_distance = length, pos-index
                    break
            if best_length:
                out[flag_pos] |= 1 << bit
                value = ((best_length-3) << 12) | (best_distance-1)
                out.extend(value.to_bytes(2, 'big'))
                pos += best_length
            else:
                out.append(data[pos])
                pos += 1
    return bytes(out)


def text_records(data):
    """Parse observed EVET length-prefixed records; preserve opaque metadata."""
    if len(data) < 4 or struct.unpack_from('<I', data)[0] != len(data)-4:
        raise ValueError('EVET payload size mismatch')
    pos = 4
    result = []
    while pos < len(data):
        if pos + 8 > len(data):
            raise ValueError('Truncated EVET record')
        command, kind, size, text_id = struct.unpack_from('<4H', data, pos)
        if size < 12 or size % 4 or pos + size > len(data):
            raise ValueError('Invalid EVET record size')
        raw = data[pos+8:pos+size]
        if b'\0' not in raw:
            raise ValueError('EVET record lacks terminator')
        result.append({'offset': pos, 'command': command, 'kind': kind,
                       'size': size, 'text_id': text_id,
                       'text': raw.split(b'\0', 1)[0]})
        pos += size
    return result


def compress_lz10_padded(data):
    """Preserve BEBF archive convention: zero-pad compressed streams to 4 bytes."""
    stream = compress_lz10(data)
    return stream + bytes((-len(stream)) % 4)
