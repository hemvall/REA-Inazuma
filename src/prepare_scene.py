"""Build an EXPERIMENTAL standalone scene from measured original SSD helpers.

This changes resource-level entry callbacks. It does not patch native ARM9
title/menu/new-game dispatch. Runtime acceptance is mandatory before release.
"""
import json
from pathlib import Path
import struct
from nds import read_rom, sha
from ie2_formats import unpack_index, decompress_lz10, compress_lz10_padded, text_records
from ssd import Program, helper_prefix, expression, variable, fixed, string, read_ssd
from scene_background import show_background

BASE = 'data_iz/script/fr/'


def prepare(rom, config):
    if sha(rom.data) != config['rom_sha256']:
        raise ValueError('Unsupported ROM')
    resources = {}
    for name in ('eve.pkb', 'eve.pkh', 'evet.pkb', 'evet.pkh'):
        start, end = rom.files[BASE+name]
        resources[name] = rom.data[start:end]
    indices = {stem: unpack_index(resources[stem+'.pkh'], resources[stem+'.pkb']) for stem in ('eve', 'evet')}
    if [r[0] for r in indices['eve']] != [r[0] for r in indices['evet']]:
        raise ValueError('Script/text key mismatch')

    def original_pair(key):
        i = next(i for i, row in enumerate(indices['eve']) if row[0] == key)
        pair = []
        for stem in ('eve', 'evet'):
            _, offset, size = indices[stem][i]
            pair.append(decompress_lz10(resources[stem+'.pkb'][offset:offset+size])[0])
        return pair

    def common(key):
        return Program(*helper_prefix(*original_pair(key)))

    # Resolve all unit IDs against actual named fixed-width ROM records.
    start, end = rom.files['data_iz/logic/fr/unitbase.dat']
    unitbase = rom.data[start:end]
    start,end = rom.files['data_iz/logic/fr/unitno.dat']
    unitno = rom.data[start:end]
    full_names = {'Mark': 'Mark Evans', 'Nathan': 'Nathan Swift', 'Jack': 'Jack Wallside',
                  'Hatch': 'Daniel Hatch', 'Byron': 'Byron Love'}
    for character in config['characters']:
        record = character.get('base_index', character['unit'])
        pos = record*96
        observed = unitbase[pos:pos+32].split(b'\0')[0].decode('ascii')
        native_id = struct.unpack_from('<H',unitno,record*2)[0]
        if observed != full_names[character['name']] or native_id != character['unit']:
            raise ValueError('Character name/unit mapping mismatch')

    chapter = common(21010000)
    # The original river-training flag is a persistent marker, unlike the event
    # counter which native match return may reset. It prevents reentrant launch.
    begin = chapter.function(0x1017, expression(0x7002, expression(0x7003,
        variable(0x10005), config['standalone_story_flag'])))
    chapter.emit(0x2009)
    chapter.emit(0x200A)
    chapter.emit(0x2010, config['entry_key'])
    chapter.end(begin)
    chapter_pair = chapter.encode()

    event = common(config['entry_key'])
    portraits = {c['name']: c.get('portrait_unit', c['unit']) for c in config['characters']}
    portraits.update({c['name']: c['unit'] for c in config['opponents']['players']})

    def opponents():
        for i, player in enumerate(config['opponents']['players']):
            event.emit(0x3059, player['unit'], 0)
            event.emit(0x3058, player['unit'], 0)
            event.emit(0x305A, player['unit'], 0, fixed(5.8+i*1.4), fixed(0.29), fixed(-18.7))
            event.emit(0x305C, player['unit'], 0, fixed(90))

    def cast():
        event.emit(0x2011)
        # Same deletion pattern as original cutscenes; no party/team stat edits.
        for index in range(5):
            event.emit(0x3059, expression(0x4045, index), 0)
        for character in config['characters']:
            event.emit(0x3058, character['unit'], 0)
            event.emit(0x305A, character['unit'], 0, *(fixed(v) for v in character['position']))
            event.emit(0x305C, character['unit'], 0, fixed(90 if character['unit'] != 1 else 270))
        event.emit(0x201A, 1)
        event.emit(0x3004, 0, 20)
        event.emit(0x3002, 30)
        if config.get('backgrounds'):
            show_background(event, config['backgrounds'][0])

    text_id = max((struct.unpack_from('<H', record, 6)[0] for record in event.texts), default=0) + 1

    def lines(dialogues, staged=False):
        nonlocal text_id
        for index, line in enumerate(dialogues):
            breaks = config.get('scene_breaks_before_line', [])
            if staged and index in breaks and index and config.get('backgrounds'):
                scene = breaks.index(index)
                show_background(event, config['backgrounds'][scene % len(config['backgrounds'])], True)
            event.emit(0x301A, 1, portraits[line['speaker']], 0, 1, 0, -1)
            event.emit(0x301D, string(line['text'], 1, text_id))
            text_id += 1
        event.emit(0x301E)

    aftermath_helper = max(r.args[1] for r in event.rows if r.opcode == 0x3001)+1
    # The chapter requeues this scene only after the map is fully loaded.
    # Store the outcome in the persistent story flag, not reset-prone counters.
    begin = event.function(aftermath_helper)
    event.assign(0x10008, 21)
    cast()
    opponents()
    for outcome in ('victory', 'defeat'):
        result = expression(0x7003, variable(0x10005), config['post_match_victory_flag'])
        if outcome == 'defeat':
            result = expression(0x7002, result)
        event.emit(0x6008, result)
        branch = event.emit(0x6001, 1, 0)
        lines(config[outcome])
        event.end(branch)
    lines(config['aftermath'])
    event.assign(0x10005, config['completed_story_flag'])
    for character in config['opponents']['players']:
        event.emit(0x3059, character['unit'], 0)
    event.assign(0x10008, 0)
    event.emit(0x2000)
    event.emit(0x2015)
    event.emit(0x2014)
    event.end(begin)

    # The item queues this callback on interaction; arrival never launches it.
    begin = event.function(0x1023)
    event.emit(0x2012)
    pending = expression(0x700E,
        expression(0x7003, variable(0x10005), config['post_match_victory_flag']),
        expression(0x7003, variable(0x10005), config['post_match_defeat_flag']))
    event.emit(0x6008, pending)
    after_match = event.emit(0x6001, 1, 0)
    event.emit(aftermath_helper)
    event.end(after_match)
    event.emit(0x600C, 1)
    play_match = event.emit(0x6001, 1, 0)
    event.assign(0x10008, 2)
    cast()
    completed = expression(0x7003, variable(0x10005), config['completed_story_flag'])
    event.emit(0x6008, expression(0x7002, completed))
    first_time = event.emit(0x6001, 1, 0)
    lines(config['opening'], staged=True)
    opponents()
    lines(config['opponent_reveal'])
    event.end(first_time)
    event.emit(0x6008, completed)
    replay = event.emit(0x6001, 1, 0)
    opponents()
    lines(config['replay'])
    event.end(replay)
    event.emit(0x3005, 1, 30)
    if config.get('backgrounds'):
        event.emit(0x202B, 1, 0)
    for character in config['characters']:
        event.emit(0x3059, character['unit'], 0)
    for character in config['opponents']['players']:
        event.emit(0x3059, character['unit'], 0)
    # Original match-launch sequence in event 22010700 (function 0x2024).
    event.emit(0x4058, 4)
    event.assign(0x10008, 10)
    event.assign(0x1000A, 3)
    event.assign(0x1002D, 1)
    # Pin the return event instead of querying an asynchronously entered slot.
    # Literal self-registration is present in original event 29020002, row 833.
    # Native match helper 0x200C reloads event slot 2 from global 0x1001A.
    event.assign(0x1001A, config['entry_key'])
    event.emit(0x4048, config['entry_key'])
    event.emit(0x4046, config['native_match_id'])
    event.emit(0x4016, 2)
    event.end(play_match)
    event.end(begin)

    # Native return can reset the event counter before dispatch. Do not gate the
    # return callback on the pre-match counter; branch on the result inside it.
    begin = event.function(0x1013)
    # Re-enter the real map before staging the aftermath. Match rendering is
    # still active at native return; actors alone do not restore world scenery.
    for outcome, flag in (('victory', config['post_match_victory_flag']),
                          ('defeat', config['post_match_defeat_flag'])):
        result = expression(0x7003, variable(0x10009), 1)
        if outcome == 'defeat':
            result = expression(0x7002, result)
        event.emit(0x6008, result)
        branch = event.emit(0x6001, 1, 0)
        event.assign(0x10005, flag)
        event.end(branch)
    event.emit(0x3005, 0, 15)
    event.emit(0x4090, string(config['map']), -1, fixed(90),
               *(fixed(v) for v in config['exploration']['spawn']))
    event.emit(0x2014)
    event.end(begin)

    generated = {config['entry_key']: event.encode()}
    # Disconnect all original chapter dispatchers, including old-save chapter loads.
    for chapter_no in range(1, 12):
        generated[21000000+chapter_no*10000] = chapter_pair
    # Keep the original map loader and return queue intact for free movement.
    first_ssd, first_sst = original_pair(21010000)
    from scene_exploration import exploration_chapter
    generated[21010000] = exploration_chapter(first_ssd, first_sst, config)
    from scene_archive import replace_entries
    edits, details = [], []
    for pair in generated.values():
        read_ssd(pair[0])
        text_records(pair[1])
    for component, stem in enumerate(('eve', 'evet')):
        replacements = {}
        originals = {key: (i, offset, size) for i, (key, offset, size) in enumerate(indices[stem])}
        for key, pair in generated.items():
            i, offset, size = originals[key]
            decoded = pair[component]
            old_decoded = decompress_lz10(resources[stem+'.pkb'][offset:offset+size])[0]
            if decoded != old_decoded:
                replacements[key] = compress_lz10_padded(decoded)
                if decompress_lz10(replacements[key])[0] != decoded:
                    raise ValueError('Compression round trip failed')
        new_header, new_blob, placements = replace_entries(
            resources[stem+'.pkh'], resources[stem+'.pkb'], replacements)
        # Include changed alignment padding when selected slots are repacked.
        source = resources[stem+'.pkb']
        for field in range(0, len(source), 4096):
            before, after = source[field:field+4096], new_blob[field:field+4096]
            if before != after:
                edits.append({'path': BASE+stem+'.pkb', 'resource_sha256': sha(source),
                    'offset': field, 'before_hex': before.hex(), 'after_hex': after.hex()})
        for key, pair in generated.items():
            i, offset, size = originals[key]
            # A donor's scrubbed tail may now hold another selected script.
            for suffix, field, length in (('.pkh', 0x30+i*12, 12),):
                source = resources[stem+suffix]
                target = new_blob if suffix == '.pkb' else new_header
                before, after = source[field:field+length], target[field:field+length]
                if before != after:
                    edits.append({'path': BASE+stem+suffix,
                        'resource_sha256': sha(source), 'offset': field,
                        'before_hex': before.hex(), 'after_hex': after.hex()})
            new_offset = placements.get(key, offset)
            new_size = len(replacements[key]) if key in replacements else size
            details.append({'entry_key': key, 'archive': stem, 'offset': new_offset,
                'original_offset': offset, 'old_compressed_size': size,
                'new_compressed_size': new_size, 'relocated': new_offset != offset,
                'unchanged': key not in replacements, 'decoded_sha256': sha(pair[component])})

    from scene_team import prepare_team
    team_edits, team_evidence = prepare_team(rom, tuple(config['team']['units']))
    edits.extend(team_edits)
    from scene_opponents import prepare_opponents
    opponent_edits, opponent_evidence = prepare_opponents(rom, config)
    edits.extend(opponent_edits)
    from scene_match_return import prepare_match_return
    return_edits, return_evidence = prepare_match_return(rom)
    edits.extend(return_edits)
    return {'rom_sha256': config['rom_sha256'], 'edits': edits}, {
        'status': 'EXPERIMENTAL: gameplay not tested', 'native_boot_bypass': False,
        'campaign_callbacks_replaced': True, 'entry_key': config['entry_key'],
        'team': team_evidence,
        'opponents': opponent_evidence,
        'match_return': return_evidence,
        'map': config['map'], 'native_match_id': config['native_match_id'],
        'exploration': config['exploration'],
        'entries': details, 'event_callbacks': ['0x1023 (item interaction)',
            '0x1013 (restore map)', 'shared aftermath helper before engine callbacks']}


def main():
    config = json.loads(Path('story/standalone_scene.json').read_text(encoding='utf-8'))
    manifest, report = prepare(read_rom('rom/original.nds'), config)
    Path('local/scene_patch.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    Path('build/scene_details.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Prepared {len(report["entries"])} resource entries. New scene and isolated chapter callbacks.')
    print('EXPERIMENTAL: native title/menu bypass not implemented; gameplay validation required.')


if __name__ == '__main__':
    main()
