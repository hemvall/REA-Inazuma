"""Native scene transitions measured in the supported French ROM.

Raimon walks: EVE 22010700, initial 1023 callback, 6013/6014 child threads
with staggered 3066 walks at 0.0625. Alien arrival: EVE 22080100 rows 899,
903-907, SFX 770 from 2D_170 and white fade mode 33 with five-frame ramps.
"""
from ssd import fixed, string


def gather_raimon(program, characters):
    """Keep controlled Mark in place; have each teammate walk into formation."""
    program.emit(0x301E)
    program.emit(0x3005, 1, 12)
    program.emit(0x2011)
    program.emit(0x3069, 1, 0)
    for i, character in enumerate(characters):
        if character['name'] == 'Mark':
            continue
        x,y,z = character['position']
        program.emit(0x3059, character['unit'], 0)
        program.emit(0x3058, character['unit'], 0)
        program.emit(0x305A, character['unit'], 0, fixed(x), fixed(y), fixed(z+5.5+i*0.25))
        program.emit(0x305C, character['unit'], 0, fixed(90))
    mark = next(c for c in characters if c['name'] == 'Mark')
    program.emit(0x201A, 1)
    program.emit(0x3062, 3, *(fixed(v) for v in mark['position']), 0, fixed(0))
    program.emit(0x3004, 1, 15)
    program.emit(0x6013, 0)
    parallel = program.emit(0x6001, 2, 0)
    # The base order keeps Jack/Hatch arriving first and Nathan closing the group.
    ordered = sorted(characters, key=lambda c: ['Mark','Jack','Hatch','Byron','Nathan'].index(c['name']))
    for i, character in enumerate(ordered):
        program.emit(0x6014, i*5)
        child = program.emit(0x6001, 3, 0)
        program.emit(0x3066, character['unit'], 0,
                     *(fixed(v) for v in character['position']), fixed(0.0625))
        if character['name'] == 'Mark':
            program.emit(0x305C, 1, 0, fixed(270))
        else:
            program.emit(0x306F, character['unit'], 0, 1, 0)
        program.end(child)
    program.end(parallel)
    program.emit(0x3002, 20)


def begin_enemy_arrival(program):
    program.emit(0x301E)
    program.emit(0x3002, 30)
    program.emit(0x3014, 1, string('2D_170'))
    program.emit(0x3015, 1, 770)
    program.emit(0x3005, 33, 5)


def end_enemy_arrival(program, characters, leader):
    program.emit(0x3004, 33, 5)
    for character in characters:
        program.emit(0x306F, character['unit'], 0, leader, 0)
    program.emit(0x3002, 30)
