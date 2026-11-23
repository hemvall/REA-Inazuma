"""Read eligible players from the user's local English Souls 2 ROM."""
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path
import struct

from arena_graphics import FACE, HEAD_PACKS
from ie2_formats import decompress_lz10, unpack_index
from nds import read_rom, sha


# Curated entries with a playable record and all five graphic resources.
PLAYERS = {
    187: 'Tezcat', 194: 'Bailong', 216: 'Jean Pierre Lapin',
    232: 'Samguk Han', 353: 'Gabriel Garcia', 440: 'Ryoma Nishiki',
    633: 'Victor Blade', 714: 'Arion Sherwind', 2186: 'Arion Sherwind',
}
GRAPHIC_PACKS = (FACE, *(f'data_iz/model/char/{name}' for name in HEAD_PACKS))
FIELD_FILES = tuple(f'data_iz/spr/char/{name}.{extension}'
                    for name in ('pcb', 'pch', 'ppb', 'pph') for extension in ('pkh', 'pkb'))


def local_source():
    configured = os.environ.get('INAZUMIA_SOULS2_ROM')
    candidates = (Path(configured),) if configured else (
        Path(__file__).resolve().parents[1] / 'rom/souls2.nds',
        Path.home() / 'Downloads/IE Souls 2 Extreme.nds',
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise ValueError('Place la ROM Souls 2 Extreme dans rom/souls2.nds pour utiliser ces joueurs.')


def source_players():
    path = local_source()
    s = path.stat()
    return read_players(path, s.st_mtime_ns, s.st_size)


@lru_cache(maxsize=1)
def read_players(path, mtime, size):
    rom = read_rom(path)
    if rom.data[12:16] != b'BEEP':
        raise ValueError('La ROM Souls 2 attendue est l’édition anglaise européenne.')

    def resource(path):
        if path not in rom.files:
            raise ValueError('Cette ROM ne contient pas les ressources Souls 2 attendues.')
        return rom.data[slice(*rom.files[path])]

    base = resource('data_iz/logic/en/unitbase.dat')
    stats = resource('data_iz/logic/en/unitstat.dat')
    match_stats = resource('data_iz/logic01/en/unitstat.dat')
    results = {}
    for index in range(len(base) // 96):
        record = base[index * 96:(index + 1) * 96]
        unit, model = struct.unpack_from('<HH', record, 66)
        if unit not in PLAYERS:
            continue
        name = record[:32].split(b'\0', 1)[0].decode('ascii', errors='replace')
        stat = stats[index * 80:(index + 1) * 80]
        match = match_stats[index * 80:(index + 1) * 80]
        if name != PLAYERS[unit] or record[0x55] not in (0x20, 0x40, 0x60, 0x80) or len(match) != 80:
            raise ValueError('Cette ROM ne correspond pas au catalogue Souls 2 Extreme.')
        results[unit] = {
            'base': record, 'stats': stat, 'match_stats': match, 'model': model,
            'name': name, 'short_name': record[32:64].split(b'\0', 1)[0].decode('ascii'),
            'graphics': {},
        }
    if results.keys() != PLAYERS.keys():
        raise ValueError('Des joueurs du catalogue Souls 2 sont absents de cette ROM.')
    field_hashes = {path: sha(resource(path)) for path in FIELD_FILES}
    for player in results.values():
        player['field_hashes'] = field_hashes
    for path in GRAPHIC_PACKS:
        header, blob = (resource(path + suffix) for suffix in ('.pkh', '.pkb'))
        entries = {key: (offset, length) for key, offset, length in unpack_index(header, blob)}
        for player in results.values():
            entry = entries.get(player['model'] * 100)
            if not entry:
                raise ValueError('Un modèle Souls 2 est incomplet.')
            offset, length = entry
            player['graphics'][path] = blob[offset:offset + length]
    return results


def portrait_png(unit):
    from PIL import Image

    record = source_players()[unit]
    raw, _ = decompress_lz10(record['graphics'][FACE])
    palette, palette_size = struct.unpack_from('<II', raw, 4)
    offset, pixels_size = struct.unpack_from('<II', raw, 20)
    if palette_size != 32 or pixels_size != 2048:
        raise ValueError('Portrait Souls 2 incompatible.')
    image = Image.new('P', (64, 64))
    colors = struct.unpack_from('<16H', raw, palette)
    image.putpalette([((color >> shift) & 31) * 255 // 31 for color in colors for shift in (0, 5, 10)])
    pixels = image.load()
    for tile_y in range(0, 64, 8):
        for tile_x in range(0, 64, 8):
            for y in range(tile_y, tile_y + 8):
                for x in range(tile_x, tile_x + 8, 2):
                    pixels[x, y] = raw[offset] & 15
                    pixels[x + 1, y] = raw[offset] >> 4
                    offset += 1
    output = BytesIO()
    image.save(output, format='PNG', transparency=0)
    return output.getvalue()
