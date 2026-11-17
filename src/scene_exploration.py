"""Native clubhouse exploration, using the original map loader and item actors.

308C/2004 is the original collectible sparkle in 22010780. Its 1014
interaction identifies the actor with 4015 and its group with 405F.
No ARM9 patch, synthetic map renderer or polling of emulator input is used.
"""
from ie2_formats import text_records
from ssd import Program, read_ssd, expression, variable, string, fixed
from scene_team import isolate_first_chapter_roster


def exploration_chapter(ssd, sst, config):
    rows, header = read_ssd(isolate_first_chapter_roster(ssd))
    records = text_records(sst)
    texts = [sst[r['offset']:r['offset']+r['size']] for r in records]
    in_callback = False
    # Preserve new-game recruitment, portal registration, shared helpers and all
    # instruction/text references. Stop campaign event requests at their callers,
    # rather than redirecting the shared queue (which also handles event return).
    for row in rows:
        if row.opcode == 0x3001:
            in_callback = row.args[1] < 0x2000
        if in_callback and row.opcode in (0x2010, 0x200F, 0x2009, 0x200A):
            row.opcode, row.types, row.args = 0x3002, [1], [0]
    start = rows[2662]
    if start.opcode != 0x4019 or records[start.args[0]]['text'] != b'mr07i02':
        raise ValueError('Unexpected native new-game map load')
    if len(config['map']) != 7:
        raise ValueError('Native map name must contain seven ASCII characters')
    texts[start.args[0]] = texts[start.args[0]].replace(b'mr07i02', config['map'].encode('ascii'))
    p = Program(rows, texts, header)
    explore = config['exploration']
    on_map = lambda: expression(0x7011, expression(0x4027), string(config['map']))
    begin = p.function(0x1017, on_map())
    p.emit(0x308C, explore['object_unit'], explore['object_group'],
           *(fixed(v) for v in explore['object_position']))
    p.emit(0x6008, expression(0x7003, variable(0x10005), 10100))
    branch = p.emit(0x6001, 1, 0)
    p.assign(0x10005, config['standalone_story_flag'])
    p.emit(0x305A, expression(0x4045, 0), 0, *(fixed(v) for v in explore['spawn']))
    p.emit(0x305C, expression(0x4045, 0), 0, fixed(90))
    p.end(branch)
    pending = expression(0x700E,
        expression(0x7003, variable(0x10005), config['post_match_victory_flag']),
        expression(0x7003, variable(0x10005), config['post_match_defeat_flag']))
    p.emit(0x6008, pending)
    branch = p.emit(0x6001, 1, 0)
    p.emit(0x2010, config['entry_key'])
    p.end(branch)
    p.end(begin)
    # All three guards must hold: map, actor identity and instance group.
    # 6012 accepts multiple guards in the original scripts; nest the conjunction
    # here using native bitwise AND on the boolean expression results.
    guard = expression(0x700F, on_map(),
        expression(0x7003, expression(0x4015), explore['object_unit']),
        expression(0x7003, expression(0x405F), explore['object_group']))
    begin = p.function(0x1014, guard)
    p.emit(0x2010, config['entry_key'])
    p.end(begin)
    return p.encode()
