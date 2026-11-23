"""Append selected head and portrait resources to the arena ROM."""
import struct

from ie2_formats import unpack_index
from nds import Rom, crc16

FACE = 'data_iz/face2d/fac'
HEAD_PACKS = ('pbf', 'pbh', 'psf', 'psh')


def relocate_graphics(rom, replacements):
    data = rom.data
    by_start = {rom.files[path]: contents for path, contents in replacements.items()}
    fat_offset, fat_size = struct.unpack_from('<II', data, 0x48)
    entries = sorted((*(struct.unpack_from('<II', data, offset)), offset)
                     for offset in range(fat_offset, fat_offset + fat_size, 8))
    first = min(start for start, _ in by_start)
    last = max(end for _, end, _ in entries)
    added = sum((len(contents) - (end - start) + 15) & ~15
                for (start, end), contents in by_start.items())
    if last + added > len(data) or any(byte != 255 for byte in data[last:last + added]):
        raise ValueError('Pas de place libre pour les ressources graphiques des joueurs.')
    # All executable and header-referenced regions must precede the moved NitroFS files.
    fixed_ends = [fat_offset + fat_size, struct.unpack_from('<I', data, 0x68)[0] + 0x840]
    for offset, length in ((0x20, 0x2C), (0x30, 0x3C), (0x40, 0x44), (0x50, 0x54), (0x58, 0x5C)):
        fixed_ends.append(struct.unpack_from('<I', data, offset)[0] + struct.unpack_from('<I', data, length)[0])
    if first < max(fixed_ends):
        raise ValueError('Les archives graphiques chevauchent une région fixe de la ROM.')
    updated = bytearray(data)
    old_cursor, shift = first, 0
    for start, end, offset in entries:
        if start < first:
            continue
        if shift and old_cursor < start:
            updated[old_cursor + shift:start + shift] = data[old_cursor:start]
        new_start = start + shift
        contents = by_start.get((start, end))
        if contents is not None:
            new_end = new_start + len(contents)
            updated[new_start:new_end] = contents
            growth = (len(contents) - (end - start) + 15) & ~15
            updated[new_end:end + shift + growth] = b'\xff' * (end + shift + growth - new_end)
            shift += growth
        else:
            new_end = end + shift
            if shift:
                updated[new_start:new_end] = data[start:end]
        struct.pack_into('<II', updated, offset, new_start, new_end)
        old_cursor = end
    if shift:
        used_size = struct.unpack_from('<I', data, 0x80)[0]
        struct.pack_into('<I', updated, 0x80, max(last, used_size) + shift)
        struct.pack_into('<H', updated, 0x15E, crc16(updated[:0x15E]))
    return Rom(updated).data


def add_graphics(data, imported):
    rom = Rom(data)
    replacements = {}
    for path in (FACE, *(f'data_iz/model/char/{name}' for name in HEAD_PACKS)):
        header = data[slice(*rom.files[path + '.pkh'])]
        blob = data[slice(*rom.files[path + '.pkb'])]
        rows = unpack_index(header, blob)
        graphics = [(model * 100, record['graphics'][path]) for model, record in imported.items()]
        if any(key <= max(row[0] for row in rows) for key, _ in graphics):
            raise ValueError('Identifiant graphique réservé déjà utilisé.')
        count = len(rows) + len(graphics)
        index = bytearray(header[:48] + bytes(12 * count))
        index.extend(bytes((-len(index)) % 16))
        struct.pack_into('<H', index, 0x10, len(index))
        struct.pack_into('<HII', index, 0x16, count, 4,
                         max(*(len(packed) for _, packed in graphics), *(row[2] for row in rows)))
        archive = bytearray()
        for row, (entry, offset, length) in enumerate(rows):
            struct.pack_into('<III', index, 48 + 12 * row, entry, len(archive), length)
            archive.extend(blob[offset:offset + length])
        for row, (key, packed) in enumerate(sorted(graphics), len(rows)):
            struct.pack_into('<III', index, 48 + 12 * row, key, len(archive), len(packed))
            archive.extend(packed)
        if len(archive) < len(blob):
            archive.extend(b'\xff' * (len(blob) - len(archive)))
        unpack_index(index, archive)
        replacements[path + '.pkh'] = index
        replacements[path + '.pkb'] = archive
    return relocate_graphics(rom, replacements)
