"""Small, bounds-checked SSD/SST reader and emitter for measured IE2 bytecode.

Binary fields cross-checked with SceneScriptData (MIT) documentation and BEBF.
References in this ROM are instruction IDs (one-based), not zero-based indexes.
Only literal calls, expressions, function guards and function blocks are emitted.
"""
from dataclasses import dataclass
import struct
from ie2_formats import text_records


@dataclass
class Instruction:
    id: int
    opcode: int
    unknown: int
    types: list
    args: list

    def encode(self):
        count = len(self.args)
        packed = bytearray(4*((count+7)//8))
        for i, kind in enumerate(self.types):
            packed[i//2] |= kind << (4*(i % 2))
        size = 8 + len(packed) + 4*count
        return struct.pack('<HHHBB', self.id, size, self.opcode, count, self.unknown) + packed + struct.pack('<'+'I'*count, *(v & 0xFFFFFFFF for v in self.args))


def read_ssd(data):
    if len(data) < 32 or data[:4] != b'SSD\0':
        raise ValueError('Invalid SSD header')
    version, file_size, count, text_count, inst_size, text_size, pad0, pad1 = struct.unpack_from('<IIHHIIII', data, 4)
    if version != 0x30001 or len(data) != 32+inst_size or file_size != len(data)+text_size:
        raise ValueError('Unsupported SSD size/version')
    rows = []
    pos = 32
    for i in range(count):
        if pos+8 > len(data):
            raise ValueError('Truncated instruction')
        ident, size, opcode, argc, unknown = struct.unpack_from('<HHHBB', data, pos)
        packed_size = 4*((argc+7)//8)
        if size != 8+packed_size+4*argc or pos+size > len(data) or ident != i+1:
            raise ValueError('Unsupported instruction layout/numbering')
        packed = data[pos+8:pos+8+packed_size]
        kinds = [(packed[n//2] >> (4*(n % 2))) & 15 for n in range(argc)]
        args = list(struct.unpack_from('<'+'I'*argc, data, pos+8+packed_size))
        rows.append(Instruction(ident, opcode, unknown, kinds, args))
        pos += size
    if pos != len(data):
        raise ValueError('Trailing instruction bytes')
    for row in rows:
        for kind, value in zip(row.types, row.args):
            if kind == 4 and not 1 <= value <= len(rows):
                raise ValueError('Instruction reference outside SSD')
        if row.opcode in (0x6001, 0x6002):
            if len(row.args) != 2 or not 1 <= row.args[1] <= len(rows):
                raise ValueError('Block reference outside SSD')
            paired = rows[row.args[1]-1]
            other_opcode = 0x6002 if row.opcode == 0x6001 else 0x6001
            if paired.opcode != other_opcode or paired.args != [row.args[0], row.id]:
                raise ValueError('Mismatched block pair')
    return rows, {'version': version, 'text_count': text_count, 'text_size': text_size,
                  'pad0': pad0, 'pad1': pad1}


def helper_prefix(ssd, sst):
    """Retain common functions, removing every original engine event callback."""
    rows, header = read_ssd(ssd)
    cut = next((i for i, r in enumerate(rows) if r.opcode == 0x3001 and r.args[1] < 0x2000), len(rows))
    prefix = rows[:cut]
    for row in prefix:
        if any(t == 4 and v > cut for t, v in zip(row.types, row.args)):
            raise ValueError('Shared helper references removed callback')
    records = [r for r in text_records(sst) if r['command'] <= cut]
    # All prefix string arguments must still resolve to their original SST rows.
    for row in prefix:
        for t, v in zip(row.types, row.args):
            if t == 3 and (v >= len(records) or records[v]['command'] != row.id):
                raise ValueError('Non-prefix/shared SST indexing is unsupported')
    raw_records = [sst[r['offset']:r['offset']+r['size']] for r in records]
    return prefix, raw_records, header


def integer(value):
    return (1, value)


def fixed(value):
    return (2, round(value*4096))


def variable(value, write=False):
    return (6 if write else 5, value)


def expression(opcode, *args):
    return ('call', opcode, args)


def string(value, kind=2, text_id=0):
    return ('text', value, kind, text_id)


class Program:
    def __init__(self, rows=(), texts=(), header=None):
        self.rows = list(rows)
        self.texts = list(texts)
        self.header = header or {'version': 0x30001, 'pad0': 0, 'pad1': 0}
        self.ordinal = sum(r.opcode == 0x3001 for r in self.rows)

    def emit(self, opcode, *args):
        row = Instruction(len(self.rows)+1, opcode, 1, [], [])
        self.rows.append(row)
        for arg in args:
            if isinstance(arg, int):
                kind, value = 1, arg
            elif arg[0] == 'call':
                kind, value = 4, self.emit(arg[1], *arg[2]).id
            elif arg[0] == 'text':
                _, text, text_kind, text_id = arg
                raw = text.encode('ascii')
                if b'\0' in raw:
                    raise ValueError('Embedded string terminator')
                size = (8+len(raw)+1+3) & ~3
                kind, value = 3, len(self.texts)
                self.texts.append(struct.pack('<4H', row.id, text_kind, size, text_id) + raw + bytes(size-8-len(raw)))
            else:
                kind, value = arg
            row.types.append(kind)
            row.args.append(value)
        return row

    def function(self, func_id, guard=None):
        self.ordinal += 1
        self.emit(0x3001, self.ordinal, func_id)
        if guard is not None:
            self.emit(0x6012, guard)
        opened = self.emit(0x6001, 0, 0)
        return opened

    def end(self, opened):
        closed = self.emit(0x6002, opened.args[0], opened.id)
        opened.args[1] = closed.id

    def assign(self, ident, value):
        self.emit(0x7001, variable(ident, write=True), value)

    def encode(self):
        body = b''.join(r.encode() for r in self.rows)
        text_body = b''.join(self.texts)
        sst = struct.pack('<I', len(text_body)) + text_body
        header = b'SSD\0' + struct.pack('<IIHHIIII', self.header['version'],
            32+len(body)+len(text_body), len(self.rows), len(self.texts), len(body),
            len(text_body), self.header['pad0'], self.header['pad1'])
        ssd = header+body
        read_ssd(ssd)
        text_records(sst)
        for r in self.rows:
            for t, v in zip(r.types, r.args):
                if t == 3 and (v >= len(self.texts) or struct.unpack_from('<H', self.texts[v])[0] != r.id):
                    raise ValueError('Invalid SST command binding')
        return ssd, sst
