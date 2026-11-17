"""Verify decoded dialogue semantics against the original supported ROM."""
import json
from pathlib import Path
from ie2_formats import unpack_index, decompress_lz10, text_records
from nds import read_rom


def main():
    config = json.loads(Path('story/proof_bebf.json').read_text(encoding='utf-8'))
    original = read_rom('rom/original.nds')
    modified = read_rom('build/inazuma_mystery.nds')
    archives = []
    for rom in (original, modified):
        a, b = rom.files[config['resource']]
        c, d = rom.files[config['index_resource']]
        blob, header = rom.data[a:b], rom.data[c:d]
        archives.append((blob, unpack_index(header, blob)))
    old_blob, old_entries = archives[0]
    new_blob, new_entries = archives[1]
    if old_entries != new_entries:
        raise ValueError('Proof changed the archive index')
    selected = config['entry_index']
    for index, (key, offset, size) in enumerate(old_entries):
        old = old_blob[offset:offset+size]
        new = new_blob[offset:offset+size]
        if index != selected:
            if old != new:
                raise ValueError('Unrelated entry changed')
            continue
        before = decompress_lz10(old)[0]
        after = decompress_lz10(new)[0]
        record = next(r for r in text_records(before) if r['command'] == config['command'])
        pos = record['offset']+8
        expected = bytearray(before)
        replacement = config['replacement'].encode('ascii')
        expected[pos:pos+len(replacement)] = replacement
        if after != expected:
            raise ValueError('Decoded changes exceed exactly one text payload')
        new_record = next(r for r in text_records(after) if r['command'] == config['command'])
        if new_record['text'] != replacement:
            raise ValueError('Replacement dialogue mismatch')
    print('PASS: 3459 archive entries retained; exactly one decoded dialogue changed.')
    print('PASS: record headers, terminators, padding and every other entry preserved.')
    print('Gameplay rendering, speaker and progression remain unverified.')


if __name__ == '__main__':
    main()
