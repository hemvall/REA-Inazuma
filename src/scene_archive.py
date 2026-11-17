"""Allocate longer authored entries inside space reclaimed from replaced scripts.

Keep the NitroFS allocation and every unrelated archive entry unchanged. Only
selected entries can donate their former slots or receive new archive offsets.
"""
import struct
from ie2_formats import unpack_index


def replace_entries(header, blob, replacements):
    rows = unpack_index(header, blob)
    by_key = {key: (i, offset, size) for i, (key, offset, size) in enumerate(rows)}
    if not set(replacements) <= by_key.keys():
        raise ValueError('Replacement key absent from archive')
    extents = sorted((offset, offset+size) for _, offset, size in rows if size)
    if any(end > start for (_, end), (start, _) in zip(extents, extents[1:])):
        raise ValueError('Original archive entries overlap')
    placements, free, pending = {}, [], []
    for key, data in replacements.items():
        if not data or len(data) % 4:
            raise ValueError('Replacement must use four-byte stream padding')
        _, offset, size = by_key[key]
        if len(data) <= size:
            placements[key] = offset
            tail = (offset+len(data)+3) & ~3
            if tail < offset+size:
                free.append([tail, offset+size])
        else:
            pending.append(key)
            free.append([offset, offset+size])
    for key in sorted(pending, key=lambda k: -len(replacements[k])):
        need = len(replacements[key])
        candidates = [span for span in free if span[1]-span[0] >= need]
        if not candidates:
            # Repack only replaced entries when several small donated tails
            # cannot hold one longer scene. Join neighboring selected slots
            # across the archive's <=15-byte alignment padding.
            pools = []
            selected = sorted((by_key[k][1], by_key[k][1]+by_key[k][2]) for k in replacements)
            for start, end in selected:
                if pools and start-pools[-1][1] <= 15 and not any(
                    k not in replacements and s and o < start and o+s > pools[-1][1]
                    for k,o,s in rows):
                    pools[-1][1] = end
                else:
                    pools.append([start,end])
            placements = {}
            for item in sorted(replacements, key=lambda k: -len(replacements[k])):
                count = len(replacements[item])
                candidates = [p for p in pools if p[1]-p[0] >= count]
                if not candidates:
                    raise ValueError(f'No reclaimed archive span fits {item}: {count} bytes')
                pool = min(candidates, key=lambda p: (p[1]-p[0],p[0]))
                placements[item] = pool[0]
                pool[0] += count
            break
        span = min(candidates, key=lambda s: (s[1]-s[0], s[0]))
        placements[key] = span[0]
        span[0] += need
    updated = bytearray(blob)
    index = bytearray(header)
    for key in replacements:
        _, offset, size = by_key[key]
        updated[offset:offset+size] = b'\xff'*size
    for key, data in replacements.items():
        i, _, _ = by_key[key]
        offset = placements[key]
        updated[offset:offset+len(data)] = data
        struct.pack_into('<II', index, 0x30+12*i+4, offset, len(data))
    unpack_index(index, updated)
    return bytes(index), bytes(updated), placements
