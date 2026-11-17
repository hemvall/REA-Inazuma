"""Generate a private binary manifest for the exact supplied BEBF revision 0 ROM."""
import json
from pathlib import Path
import struct
from nds import read_rom, sha
from ie2_formats import unpack_index, decompress_lz10, compress_lz10, text_records


def prepare(rom, config):
    if sha(rom.data) != config['rom_sha256']:
        raise ValueError('Unsupported original ROM SHA-256')
    resources = {}
    for key in ('resource', 'index_resource'):
        name = config[key]
        start, end = rom.files[name]
        resources[name] = rom.data[start:end]
    pkb = resources[config['resource']]
    pkh = resources[config['index_resource']]
    entries = unpack_index(pkh, pkb)
    index = config['entry_index']
    key, offset, size = entries[index]
    if key != config['entry_key']:
        raise ValueError('Archive entry key mismatch')
    original, consumed = decompress_lz10(pkb[offset:offset+size])
    matches = [r for r in text_records(original)
               if r['command'] == config['command'] and r['text_id'] == config['text_id']]
    if len(matches) != 1:
        raise ValueError('Unique dialogue record not found')
    record = matches[0]
    if record['offset'] != config['record_offset'] or record['kind'] != 1:
        raise ValueError('Unexpected dialogue record layout')
    if sha(record['text']) != config['original_text_sha256']:
        raise ValueError('Original text hash mismatch')
    replacement = config['replacement'].encode('ascii')
    if len(replacement) != len(record['text']) or b'\0' in replacement:
        raise ValueError('Proof must preserve exact text length')
    modified = bytearray(original)
    pos = record['offset'] + 8
    modified[pos:pos+len(replacement)] = replacement
    # Record headers, null terminators, padding and every other record are untouched.
    if modified[:pos] != original[:pos] or modified[pos+len(replacement):] != original[pos+len(replacement):]:
        raise ValueError('Unexpected decompressed changes')
    encoded = compress_lz10(modified)
    if decompress_lz10(encoded)[0] != modified:
        raise ValueError('LZ10 round trip failed')
    next_offsets = [o for _, o, _ in entries if o > offset]
    limit = min(next_offsets) if next_offsets else len(pkb)
    # Existing slot only: never move entries or change archive/resource length.
    if len(encoded) > limit-offset:
        raise ValueError(f'Recompressed entry needs {len(encoded)} bytes; slot has {limit-offset}')
    edits = []

    def add(path, at, before, after):
        if before != after:
            edits.append({'path': path, 'resource_sha256': sha(resources[path]),
                          'offset': at, 'before_hex': before.hex(), 'after_hex': after.hex()})

    # Keep recorded entry size when the new stream fits. Otherwise use only proven
    # alignment slack and update this entry's PKH size; other offsets remain exact.
    span = max(size, len(encoded))
    after = encoded + pkb[offset+len(encoded):offset+span]
    add(config['resource'], offset, pkb[offset:offset+span], after)
    if len(encoded) > size:
        field = 0x30 + index*12 + 8
        add(config['index_resource'], field, pkh[field:field+4], struct.pack('<I', len(encoded)))
    return {'rom_sha256': config['rom_sha256'], 'edits': edits}, {
        'entry_index': index, 'entry_key': key, 'pkb_offset': offset,
        'original_compressed_size': size, 'original_stream_consumed': consumed,
        'new_compressed_size': len(encoded), 'slot_capacity': limit-offset,
        'decoded_size': len(original), 'record_offset': record['offset'],
        'command': record['command'], 'text_id': record['text_id'],
        'replacement': config['replacement'], 'gameplay_tested': False}


def main():
    config = json.loads(Path('story/proof_bebf.json').read_text(encoding='utf-8'))
    manifest, report = prepare(read_rom('rom/original.nds'), config)
    Path('local').mkdir(exist_ok=True)
    Path('local/patch.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    Path('build/proof_details.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(str(error))
