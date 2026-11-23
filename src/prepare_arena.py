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
    names=('prepare_arena.py','prepare_scene.py','prepare_arena_scene.py','scene_archive.py','scene_background.py','scene_team.py','scene_exploration.py','club_scene.py','native_club_scene.py','club_fixtures.py','ssd.py','ie2_formats.py','nds.py')
    return sha(b''.join((ROOT/'src'/name).read_bytes() for name in names)+
               (ROOT/'src/native_route_patch.py').read_bytes()+
               (ROOT/'story/standalone_scene.json').read_bytes())


def ensure_built(profile='arena'):
    if profile not in ('arena', 'club', 'club_native', 'club_web'): raise ValueError('Unknown arena profile')
    folder=ROOT/'build'/profile
    try:
        identity=json.loads((folder/'profile.json').read_text())
        if identity.get('source_sha256')==source_identity() and sha((folder/'arena.nds').read_bytes())==identity['rom_sha256']:
            return
    except (OSError,ValueError,KeyError):
        pass
    build(folder.name)


def scene_pair(rom):
    result = []
    for stem in ('eve', 'evet'):
        prefix = 'data_iz/script/fr/' + stem
        index = rom.data[slice(*rom.files[prefix+'.pkh'])]
        blob = rom.data[slice(*rom.files[prefix+'.pkb'])]
        _, offset, size = next(row for row in unpack_index(index, blob) if row[0] == 22010100)
        result.append(decompress_lz10(blob[offset:offset+size])[0])
    return result


def build(profile='arena'):
    if profile not in ('arena', 'club', 'club_native', 'club_web'): raise ValueError('Unknown arena profile')
    build_identity = source_identity()
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
    native_route = profile in ('club_native', 'club_web')
    if profile in ('club', 'club_native', 'club_web'):
        config['club'] = True
        config['native_club'] = native_route
        config['map'] = 'mr07i01'
        config['exploration'] = {'object_unit':261, 'object_group':28,
                                 'object_position':[0, 0.16, 2.5], 'spawn':[0, 0.16, 5.5]}
    if profile == 'club_native':
        config = json.loads((ROOT/'story/standalone_scene.json').read_text())
        config['friendly_event_key'] = 25030300
        config['seymour'] = {'unit':261, 'group':29, 'position':[8, 0.29, -15]}
    original = read_rom(ROOT/'rom/original.nds')
    manifest, _ = prepare(original, config)
    # Keep the original starting party template intact. An isolated opponent
    # slot supplies full Raimon for the friendly match, using a proven match
    # record instead of the stock debug encounter 500.
    team_path = 'data_iz/logic/fr/team.pkb'
    teams = original.data[slice(*original.files[team_path])]
    index = original.data[slice(*original.files['data_iz/logic/fr/team.pkh'])]
    keys = [struct.unpack_from('<I', index, 48+i*4)[0] for i in range(len(teams)//320)]
    raimon = bytearray(teams[keys.index(1)*320:(keys.index(1)+1)*320])
    struct.pack_into('<H', raimon, 32, 70)
    pos = keys.index(70)*320
    if not native_route:
        manifest['edits'].append({'path':team_path, 'resource_sha256':sha(teams), 'offset':pos,
            'before_hex':teams[pos:pos+320].hex(), 'after_hex':raimon.hex()})
    games_path = 'data_iz/logic/games.dat'
    games = original.data[slice(*original.files[games_path])]
    match = bytearray(games[33*48:34*48])
    if struct.unpack_from('<H', match)[0] != 10: raise ValueError('Unexpected native match table')
    struct.pack_into('<H', match, 0, 70)
    if native_route:
        from native_club_scene import route_data
        matches=bytearray()
        # The board reads its caption and badge from this separate team key,
        # independently of games.dat. Retain two existing native emblems.
        for badge,title in ((513,'Occulte vs Zeus'),(549,'Royal Academy vs Raimon')):
            at=keys.index(badge)*320
            manifest['edits'].append({'path':team_path,'resource_sha256':sha(teams),'offset':at,
                'before_hex':teams[at:at+32].hex(),
                'after_hex':title.encode('ascii').ljust(32,b'\0').hex()})
        # Key 1 refers to the current save's Raimon party. Reuse an existing
        # team slot in both tables so opponent lookups see the full roster.
        for prefix in ('data_iz/logic/fr/', 'data_iz/logic01/fr/'):
            path=prefix+'team.pkb'
            data=original.data[slice(*original.files[path])]
            idx=original.data[slice(*original.files[prefix+'team.pkh'])]
            team_keys=[struct.unpack_from('<I',idx,48+i*4)[0] for i in range(len(data)//320)]
            offset=team_keys.index(11)*320
            full_raimon=bytearray(raimon)
            struct.pack_into('<H',full_raimon,32,11)
            manifest['edits'].append({'path':path,'resource_sha256':sha(data),'offset':offset,
                'before_hex':data[offset:offset+320].hex(),'after_hex':full_raimon.hex()})
        for away in (10,11):
            # Use the postgame match script, including its native rewards and
            # field return, instead of the Occulte story encounter script.
            row=bytearray(games[363*48:364*48])
            struct.pack_into('<H',row,0,away)
            row[3]=30
            matches.extend(row)
        manifest['edits'].append({'path':games_path,'resource_sha256':sha(games),'offset':500*48,
            'before_hex':games[500*48:502*48].hex(),'after_hex':matches.hex()})
        for path in original.files:
            if 'PracticeGame1' in path and path.endswith('.dat'):
                before=original.data[slice(*original.files[path])]
                manifest['edits'].append({'path':path,'resource_sha256':sha(before),'offset':0,
                    'before_hex':before.hex(),'after_hex':route_data(before).hex()})
    else:
        manifest['edits'].append({'path':games_path, 'resource_sha256':sha(games), 'offset':500*48,
            'before_hex':games[500*48:501*48].hex(), 'after_hex':match.hex()})
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
    slots = {'roster': [], 'roster_guards': [], 'removals': [], 'removal_guards': [], 'portraits': [], 'texts': []}
    for row in rows:
        if row.opcode == 0x403E and row.args[1:] == [30, row.args[0]] and row.id > 600:
            slots['roster'].append(offset+12)
        if row.opcode == 0x7003 and row.types == [1,1] and row.args[1] == 0 and 1 <= row.args[0] <= 16 and row.id > 600:
            slots['roster_guards'].append(offset+12)
        if row.opcode == 0x403F and row.types == [1] and 0x400000 <= row.args[0] < 0x400084:
            slots['removals'].append(offset+12)
        if row.opcode == 0x7003 and row.types == [1,1] and row.args[1] == 0 and 0x400000 <= row.args[0] < 0x400084:
            slots['removal_guards'].append(offset+12)
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
    if not native_route and (len(slots['roster']) != 16 or len(slots['roster_guards']) != 16 or len(slots['texts']) != 6):
        raise ValueError('Unexpected arena slot layout')
    if not native_route and (len(slots['removals']) != 132 or len(slots['removal_guards']) != 132):
        raise ValueError('Unexpected native roster-removal slots')
    folder = ROOT/'build'/profile; folder.mkdir(parents=True, exist_ok=True)
    from validate_patch import validate
    verification=validate(original,output,manifest)
    if native_route:
        from native_route_patch import unlock_route
        output,native_verification=unlock_route(output)
        verification={'resources':verification,'native_route':native_verification,
            'original_sha256':sha(original.data),'modified_sha256':sha(output),
            'changed_bytes':sum(a!=b for a,b in zip(original.data,output)),
            'reverse_verified':True,'gameplay_tested':False}
    (folder/'scene.ssd').write_bytes(ssd)
    (folder/'scene.sst').write_bytes(sst)
    (folder/'arena.nds').write_bytes(output)
    (folder/'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    (folder/'profile.json').write_text(json.dumps({'rom_sha256':sha(output), 'source_sha256':build_identity,
        'core_sha256':'e50e675eab350e14d1cb9ccc4ada7f09fb6a3e6dcd16ef4a197d9a5b8a656f13','slots':slots,
        'global_base':0x020DBEBC, 'event_key':22010100}, indent=2))
    print('Arena shell built:', sha(output))


if __name__ == '__main__':
    build()
