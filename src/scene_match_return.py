"""Scoped match-35 return that hands off to the native world scene directly.

The tutorial challenge's original 1005 result presentation crashes this custom
episode before its 1004 return. Preserve the original result computation and
mode/slot teardown in 200F/200C, and the six tutorial completion bits from 1004.
Only this MCH entry changes; football rules, engine code and other matches stay.
"""
from ie2_formats import unpack_index, decompress_lz10, compress_lz10_padded, text_records
from ssd import read_ssd, Program
from scene_archive import replace_entries
from nds import sha
import struct

BASE = 'data_iz/script/fr/'
KEY = 24010035


def prepare_match_return(rom):
    header = rom.data[slice(*rom.files[BASE+'mch.pkh'])]
    blob = rom.data[slice(*rom.files[BASE+'mch.pkb'])]
    _, offset, size = next(r for r in unpack_index(header, blob) if r[0] == KEY)
    original = decompress_lz10(blob[offset:offset+size])[0]
    rows, metadata = read_ssd(original)
    th = rom.data[slice(*rom.files[BASE+'mcht.pkh'])]
    tb = rom.data[slice(*rom.files[BASE+'mcht.pkb'])]
    _, to, ts = next(r for r in unpack_index(th, tb) if r[0] == KEY)
    sst = decompress_lz10(tb[to:to+ts])[0]
    records = text_records(sst)
    # The specific original callback, not a search/replace across match scripts.
    if rows[289].opcode != 0x3001 or rows[289].args[1] != 0x1005 or rows[291].opcode != 0x2010:
        raise ValueError('Unexpected native challenge finish callback')
    # Replace the complete helper, including its SST records. Leaving stale
    # string records attached to no-op instructions corrupts native script load.
    prefix, suffix = rows[:203], rows[243:]
    p = Program(prefix, (), metadata)
    begin = p.function(0x2010)
    for bit in (8,16,32,512,1024,2048):
        p.emit(0x2011, bit)
    p.emit(0x200F)
    p.end(begin)
    mapping = {r.id:r.id for r in prefix}
    mapping.update({r.id:len(p.rows)+i+1 for i,r in enumerate(suffix)})
    kept_texts = [(i,r) for i,r in enumerate(records) if r['command'] in mapping]
    text_mapping = {old:new for new,(old,_) in enumerate(kept_texts)}
    for row in prefix+suffix:
        old_id = row.id
        row.id = mapping[old_id]
        for i,kind in enumerate(row.types):
            if kind == 4:
                row.args[i] = mapping[row.args[i]]
            elif kind == 3:
                row.args[i] = text_mapping[row.args[i]]
        if row.opcode in (0x6001,0x6002):
            row.args[1] = mapping[row.args[1]]
    p.rows.extend(suffix)
    for _, record in kept_texts:
        raw = bytearray(sst[record['offset']:record['offset']+record['size']])
        struct.pack_into('<H',raw,0,mapping[record['command']])
        p.texts.append(bytes(raw))
    decoded, encoded_texts = p.encode()
    replacement = compress_lz10_padded(decoded)
    new_header, new_blob, _ = replace_entries(header, blob, {KEY: replacement})
    text_replacement = compress_lz10_padded(encoded_texts)
    new_th, new_tb, _ = replace_entries(th, tb, {KEY: text_replacement})
    edits = []
    for suffix, before, after in (('mch.pkh', header, new_header), ('mch.pkb', blob, new_blob),
                                   ('mcht.pkh', th, new_th), ('mcht.pkb', tb, new_tb)):
        for pos in range(0, len(before), 4096):
            a,b = before[pos:pos+4096], after[pos:pos+4096]
            if a != b:
                edits.append({'path': BASE+suffix, 'resource_sha256': sha(before),
                              'offset': pos, 'before_hex': a.hex(), 'after_hex': b.hex()})
    return edits, {'entry_key': KEY, 'native_result_and_teardown_preserved': True,
                   'tutorial_completion_bits_preserved': True,
                   'decoded_sha256': sha(decoded), 'runtime_verified': False}
