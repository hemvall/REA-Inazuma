"""Conservative NitroFS inspection and fixed-size resource modification."""
import hashlib
import struct
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def crc16(data):
    value = 0xFFFF
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xA001 if value & 1 else 0)
    return value


class Rom:
    def __init__(self, data):
        self.data = bytes(data)
        if len(data) < 0x200:
            raise ValueError('Truncated NDS header')
        if crc16(data[:0x15E]) != struct.unpack_from('<H', data, 0x15E)[0]:
            raise ValueError('Invalid NDS header CRC16')
        self.files = {}
        fnt_offset, fnt_size, fat_offset, fat_size = struct.unpack_from('<4I', data, 0x40)
        fnt = self.slice(fnt_offset, fnt_size)
        fat = self.slice(fat_offset, fat_size)
        if len(fnt) < 8 or len(fat) % 8:
            raise ValueError('Invalid NitroFS tables')
        count = struct.unpack_from('<H', fnt, 6)[0]
        if not 1 <= count <= 4096 or count * 8 > len(fnt):
            raise ValueError('Invalid directory count')
        entries = list(struct.iter_unpack('<II', fat))
        for start, end in entries:
            if start < 0x200 or end < start or end > len(data):
                raise ValueError('Invalid FAT extent')
        extents = sorted((a, b) for a, b in entries if a != b)
        if any(b > c for (a, b), (c, d) in zip(extents, extents[1:])):
            raise ValueError('Overlapping FAT extents')
        visited = set()

        def walk(directory, prefix):
            if directory in visited or not 0 <= directory < count:
                raise ValueError('Cyclic or invalid NitroFS directory')
            visited.add(directory)
            pos, file_id, _ = struct.unpack_from('<IHH', fnt, directory * 8)
            while True:
                if pos >= len(fnt):
                    raise ValueError('Truncated FNT name list')
                tag = fnt[pos]
                pos += 1
                if tag == 0:
                    break
                length = tag & 127
                if not length or pos + length > len(fnt):
                    raise ValueError('Invalid FNT name')
                name = fnt[pos:pos + length].decode('ascii', errors='strict')
                pos += length
                if name in ('.', '..') or '/' in name or '\\' in name:
                    raise ValueError('Unsafe filename')
                path = prefix + name
                if tag & 128:
                    if pos + 2 > len(fnt):
                        raise ValueError('Truncated directory ID')
                    child = struct.unpack_from('<H', fnt, pos)[0] - 0xF000
                    pos += 2
                    walk(child, path + '/')
                else:
                    if file_id >= len(entries) or path in self.files:
                        raise ValueError('Invalid file ID or duplicate filename')
                    self.files[path] = entries[file_id]
                    file_id += 1
        walk(0, '')

    def slice(self, offset, size):
        if offset < 0x200 or offset + size > len(self.data):
            raise ValueError('Table outside ROM')
        return self.data[offset:offset + size]

    def report(self):
        return {
            'sha256': sha(self.data), 'size': len(self.data),
            'title': self.data[:12].rstrip(b'\0').decode('ascii', errors='replace'),
            'game_code': self.data[12:16].decode('ascii', errors='replace'),
            'revision': self.data[0x1E], 'unit_code': self.data[0x12],
            'language': 'Unconfirmed: verify resources and in-game language',
            'edition': 'Unconfirmed: identify exact game code before patching',
            'header_crc16_valid': True,
            'files': [{'path': p, 'offset': a, 'size': b-a,
                       'sha256': sha(self.data[a:b])}
                      for p, (a, b) in sorted(self.files.items())]}


def read_rom(path):
    if not Path(path).is_file():
        raise ValueError(f'Missing local ROM: {path}. No ROM was built.')
    return Rom(Path(path).read_bytes())


def patch(rom, manifest):
    if manifest['rom_sha256'] != sha(rom.data):
        raise ValueError('Unsupported original ROM SHA-256')
    if not manifest['edits']:
        raise ValueError('Manifest contains no confirmed edits')
    output = bytearray(rom.data)
    touched = set()
    for edit in manifest['edits']:
        start, end = rom.files[edit['path']]
        if sha(rom.data[start:end]) != edit['resource_sha256']:
            raise ValueError('Resource hash mismatch')
        before = bytes.fromhex(edit['before_hex'])
        after = bytes.fromhex(edit['after_hex'])
        offset = edit['offset']
        if not before or len(before) != len(after) or before == after:
            raise ValueError('Edits must change bytes and preserve exact length')
        if type(offset) is not int or offset < 0 or start + offset + len(before) > end:
            raise ValueError('Edit outside selected resource')
        absolute = start + offset
        span = set(range(absolute, absolute + len(before)))
        if touched & span:
            raise ValueError('Overlapping edits')
        touched.update(span)
        if rom.data[absolute:absolute + len(before)] != before:
            raise ValueError('Original bytes mismatch')
        output[absolute:absolute + len(before)] = after
    rebuilt = Rom(output)
    if rebuilt.files != rom.files or output[:0x200] != rom.data[:0x200]:
        raise ValueError('Header or filesystem changed')
    return bytes(output)
