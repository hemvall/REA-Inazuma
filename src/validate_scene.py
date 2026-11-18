"""Independently inspect the standalone candidate's callbacks and archive layout."""
import json
import argparse
from pathlib import Path
from nds import read_rom, sha
from ie2_formats import unpack_index, decompress_lz10, text_records
from ssd import read_ssd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patched', default='build/inazuma_mystery.nds')
    args = parser.parse_args()
    config = json.loads(Path('story/standalone_scene.json').read_text(encoding='utf-8'))
    original = read_rom('rom/original.nds')
    modified = read_rom(args.patched)
    if sha(original.data) != config['rom_sha256']:
        raise ValueError('Unsupported original')
    if original.files != modified.files:
        raise ValueError('NitroFS layout changed')
    base = 'data_iz/script/fr/'
    selected = {21000000+i*10000 for i in range(1, 12)} | {config['entry_key']}
    parsed = {}
    details = []
    for stem in ('eve', 'evet'):
        old = []
        new = []
        for rom, parts in ((original, old), (modified, new)):
            for suffix in ('.pkh', '.pkb'):
                start, end = rom.files[base+stem+suffix]
                parts.append(rom.data[start:end])
        old_index = unpack_index(*old)
        new_index = unpack_index(*new)
        extents = sorted((o,o+s) for _,o,s in new_index if s)
        if any(b > c for (_,b),(c,_) in zip(extents,extents[1:])):
            raise ValueError('Patched archive entries overlap')
        if len(old_index) != len(new_index):
            raise ValueError('Archive count changed')
        for before, after in zip(old_index, new_index):
            key, offset, size = before
            new_key, new_offset, new_size = after
            if key != new_key or (key not in selected and offset != new_offset):
                raise ValueError('Unselected archive key or offset moved')
            if key not in selected:
                if before != after or old[1][offset:offset+size] != new[1][offset:offset+size]:
                    raise ValueError('Unselected archive entry changed')
                continue
            owned = []
            for k,o,s in sorted(old_index, key=lambda row:row[1]):
                if k in selected:
                    if owned and 0 <= o-owned[-1][1] <= 15:
                        owned[-1] = (owned[-1][0],o+s)
                    else:
                        owned.append((o,o+s))
                else:
                    # Never join selected spans across an unrelated entry.
                    if owned and owned[-1][1] <= o:
                        owned.append((o,o))
            owned = [(a,b) for a,b in owned if a != b]
            if not any(a <= new_offset and new_offset+new_size <= b for a,b in owned):
                raise ValueError('Selected entry outside reclaimed selected slots')
            data, used = decompress_lz10(new[1][new_offset:new_offset+new_size])
            if new_size % 4 or not 0 <= new_size-used <= 3 or any(new[1][new_offset+used:new_offset+new_size]):
                raise ValueError('Invalid original-convention compressed padding')
            if stem == 'eve':
                rows, header = read_ssd(data)
                callbacks = [r.args[1] for r in rows if r.opcode == 0x3001 and r.args[1] < 0x2000]
                if key == 21010000:
                    old_rows, _ = read_ssd(decompress_lz10(old[1][offset:offset+size])[0])
                    wanted = [r.args[1] for r in old_rows if r.opcode == 0x3001 and r.args[1] < 0x2000]
                    route = rows[166]
                    if route.opcode != 0x4047 or route.types != [1,5] or route.args != [2, 9]:
                        raise ValueError('Native chapter return queue was modified')
                    wanted += [0x1017, 0x1013, 0x1014]
                    # The sole authored event request is inside the appended
                    # item interaction, never an automatic arrival callback.
                    requests = [r for r in rows if r.opcode in (0x2010, 0x200F)
                                and r.id > 556]
                    if len(requests) != 3 or any(r.args != [config['entry_key']] for r in requests):
                        raise ValueError('Unexpected campaign or automatic event request')
                    if rows[2662].opcode != 0x4019:
                        raise ValueError('Native initial map loader missing')
                    team_rows = rows[2584:2608]
                    additions = [r.args for r in team_rows if r.opcode == 0x403E]
                    expected = [[unit,1,i+1] for i,unit in enumerate(config['team']['units'])]
                    if additions != expected or any(r.opcode == 0x403F for r in team_rows):
                        raise ValueError('Native chapter still rebuilds original squad')
                else:
                    wanted = [0x1023] if key == config['entry_key'] else [0x1017]
                if callbacks != wanted:
                    raise ValueError('Unexpected reachable engine callback set')
                if key == config['entry_key']:
                    authored = rows[645:]
                    if any(r.opcode in (0x3008, 0x300F) for r in authored):
                        raise ValueError('Authored scene hides the native map with a sprite')
                    launches = [r.args for r in authored if r.opcode == 0x4046]
                    if launches != [[config['native_match_id']]]:
                        raise ValueError('Missing or duplicate native challenge launch')
                parsed[key] = (rows, header)
            else:
                records = text_records(data)
                rows, header = parsed[key]
                if header['text_count'] != len(records) or header['text_size'] != len(data)-4:
                    raise ValueError('SSD/SST header mismatch')
                for row in rows:
                    for kind, value in zip(row.types, row.args):
                        if kind == 3 and (value >= len(records) or records[value]['command'] != row.id):
                            raise ValueError('String argument does not bind to its SST record')
                if key == 21010000:
                    if records[rows[2662].args[0]]['text'] != config['map'].encode('ascii'):
                        raise ValueError('Initial map is not the authored clubhouse')
                    item = config['exploration']
                    sparkle = [r for r in rows if r.opcode == 0x308C and
                               r.args[:2] == [item['object_unit'], item['object_group']]]
                    if not any(r.args[2:] == [round(v*4096) & 0xFFFFFFFF
                                             for v in item['object_position']] for r in sparkle):
                        raise ValueError('Missing entrance interaction object')
                if key == config['entry_key']:
                    expected_lines = [line['text'].encode('ascii') for scene in
                        ('victory', 'defeat', 'aftermath', 'opening', 'opponent_reveal', 'replay') for line in config[scene]]
                    observed_lines = [records[row.args[0]]['text'] for row in rows if row.opcode == 0x301D and row.id > 645]
                    if observed_lines != expected_lines:
                        raise ValueError('Standalone dialogue differs from authored scene')
            details.append({'entry_key': key, 'archive': stem, 'decoded_sha256': sha(data)})
    allowed = {base+stem+suffix for stem in ('eve', 'evet') for suffix in ('.pkb', '.pkh')}
    # Native result animations, reward/XP screens and match teardown must survive.
    for stem in ("mch","mcht"):
        for suffix in (".pkh",".pkb"):
            path=base+stem+suffix
            if original.data[slice(*original.files[path])] != modified.data[slice(*modified.files[path])]:
                raise ValueError("Native match result/XP archive changed")
    from scene_team import TEAM_PATH, ROSTER
    import struct
    for team_path in (TEAM_PATH,'data_iz/logic/fr/team.pkb'):
        a,b = modified.files[team_path]
        team = modified.data[a:a+320]
        observed_team = [struct.unpack_from('<H',team,0x40+i*8)[0] for i in range(32)]
        if observed_team != list(ROSTER)+[0]*27 or any(team[0x44+i*8] for i in range(5)):
            raise ValueError('Initial five-player level-one template mismatch')
        oa,ob = original.files[team_path]
        allowed_tail = bytearray(original.data[oa+320:ob])
        if team_path == 'data_iz/logic/fr/team.pkb':
            from scene_opponents import prepare_opponents
            opponent_edits, _ = prepare_opponents(original, config)
            edit = opponent_edits[0]
            pos = edit['offset']-320
            allowed_tail[pos:pos+320] = bytes.fromhex(edit['after_hex'])
            if modified.data[a+edit['offset']:a+edit['offset']+320] != bytes.fromhex(edit['after_hex']):
                raise ValueError('Surprise opponent lineup differs from authored team')
        if modified.data[a+320:b] != bytes(allowed_tail):
            raise ValueError('Unrelated team template changed')
        allowed.add(team_path)
    for path, (start, end) in original.files.items():
        if path not in allowed and original.data[start:end] != modified.data[start:end]:
            raise ValueError(f'Unexpected resource edit: {path}')
    report = {'rom_sha256': sha(modified.data), 'selected_entries_verified': len(details),
              'unselected_archive_offsets_preserved': True, 'callback_sets_verified': True,
              'ssd_sst_bindings_verified': True, 'authored_dialogues_verified': True,
              'native_exploration_verified_structurally': True,
              'native_challenge_launch_verified_structurally': True,
              'surprise_opponents_verified_structurally': True,
              'native_result_archives_unchanged': True,
              'native_boot_bypass': False, 'gameplay_tested': False,
              'entries': details}
    Path('build/scene_semantics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('PASS: 24 script/text entries, references, callback sets and authored dialogues verified.')
    print('Native title/menu bypass NOT implemented. Gameplay NOT tested.')


if __name__ == '__main__':
    main()
