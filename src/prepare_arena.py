"""Build the fixed arena shell once; runtime fixtures never rebuild this ROM."""
import json
import struct
from pathlib import Path
from nds import Rom, read_rom, patch, sha
from prepare_scene import prepare
from ie2_formats import unpack_index, decompress_lz10, text_records
from ssd import read_ssd

ROOT = Path(__file__).resolve().parents[1]


def source_identity():
    names=('prepare_arena.py','prepare_scene.py','prepare_arena_scene.py','scene_archive.py','scene_background.py','scene_team.py','ssd.py','ie2_formats.py','nds.py')
    return sha(b''.join((ROOT/'src'/name).read_bytes() for name in names)+(ROOT/'story/standalone_scene.json').read_bytes())


def ensure_built():
    folder=ROOT/'build/arena'
    try:
        profile=json.loads((folder/'profile.json').read_text())
        if profile.get('source_sha256')==source_identity() and sha((folder/'arena.nds').read_bytes())==profile['rom_sha256']:
            return
    except (OSError,ValueError,KeyError):
        pass
    build()


def scene_pair(rom):
    result = []
    for stem in ('eve', 'evet'):
        prefix = 'data_iz/script/fr/' + stem
        index = rom.data[slice(*rom.files[prefix+'.pkh'])]
        blob = rom.data[slice(*rom.files[prefix+'.pkb'])]
        _, offset, size = next(row for row in unpack_index(index, blob) if row[0] == 22010100)
        result.append(decompress_lz10(blob[offset:offset+size])[0])
    return result


def build():
    config = json.loads((ROOT/'story/standalone_scene.json').read_text())
    config['arena'] = True
    config['opening'] = [{'speaker': 'Mark' if i % 2 == 0 else 'Byron',
                          'text': f'IZARENA-LINE-{i:02d} ' + '.' * 140} for i in range(6)]
    # Native pitch illustration, displayed behind the fixture captain portraits.
    config['backgrounds'] = ['c2t0806']
    config['scene_breaks_before_line'] = []
    config['victory'] = [{'speaker': 'Mark', 'text': 'Victoire ! La rencontre est terminee.'}]
    config['defeat'] = [{'speaker': 'Mark', 'text': 'Defaite. Une nouvelle rencontre nous attend.'}]
    config['native_match_id'] = 33
    original = read_rom(ROOT/'rom/original.nds')
    manifest, _ = prepare(original, config)
    # Retain valid movie lifecycle while shortening both stock cinematics.
    for name in ('data_iz/movie/op00.mods', 'data_iz/movie/fr/op00.mods', 'data_iz/movie/a2m02.mods'):
        if name not in original.files:
            continue
        data = original.data[slice(*original.files[name])]
        manifest['edits'].append({'path': name, 'resource_sha256': sha(data),
            'offset': 8, 'before_hex': data[8:12].hex(), 'after_hex': struct.pack('<I',1).hex()})
    output = patch(original, manifest)
    rom = Rom(output)
    ssd, sst = scene_pair(rom)
    rows, _ = read_ssd(ssd)
    offset = 32
    slots = {'roster': [], 'portraits': [], 'texts': []}
    for row in rows:
        if row.opcode == 0x403E and row.args[1:] == [30, row.args[0]] and row.id > 600:
            slots['roster'].append(offset+12)
        if row.opcode == 0x4046 and row.types == [1] and row.args == [33]:
            slots['match'] = offset+12
        offset += len(row.encode())
    records = text_records(sst)
    for record in records:
        raw = sst[record['offset']+8:record['offset']+record['size']]
        if raw.startswith(b'IZARENA-LINE-'):
            slots['texts'].append({'offset': record['offset']+8, 'capacity': record['size']-8})
            text_row = rows[record['command']-1]
            portrait = rows[text_row.id-2]
            if portrait.opcode != 0x301A:
                raise ValueError('Portrait/text adjacency changed')
            pos = 32 + sum(len(r.encode()) for r in rows[:portrait.id-1])
            slots['portraits'].append(pos+16)
    if len(slots['roster']) != 16 or len(slots['texts']) != 6:
        raise ValueError('Unexpected arena slot layout')
    folder = ROOT/'build/arena'; folder.mkdir(parents=True, exist_ok=True)
    from validate_patch import validate
    verification=validate(original,output,manifest)
    (folder/'scene.ssd').write_bytes(ssd)
    (folder/'scene.sst').write_bytes(sst)
    (folder/'arena.nds').write_bytes(output)
    (folder/'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    (folder/'profile.json').write_text(json.dumps({'rom_sha256':sha(output), 'source_sha256':source_identity(),
        'core_sha256':'e50e675eab350e14d1cb9ccc4ada7f09fb6a3e6dcd16ef4a197d9a5b8a656f13','slots':slots,
        'global_base':0x020DBEBC, 'event_key':22010100}, indent=2))
    print('Arena shell built:', sha(output))


if __name__ == '__main__':
    build()
