"""Measured BEBF new-game roster edits and read-only emulator verification.

Native new-game overlay 3 calls 01FFC738 with team key 1, base level 1.
01FFC328 consumes 32 eight-byte rows at team+40; byte +4 adds to base level.
The early-game logic01 library's key 1 originally contains Mark alone.
This changes that template, not just the actors displayed by a cutscene.
"""
import struct
from nds import sha
from ssd import read_ssd

ORIGINAL_SHA256 = '1e67c699a6b3ecfb5230e8c2245746879fab57123277651da74b4cc9b8ba25d3'
TEAM_PATH = 'data_iz/logic01/fr/team.pkb'
INDEX_PATH = 'data_iz/logic01/fr/team.pkh'
ROSTER = (1, 3, 29, 190, 2430)
BASE_RECORDS = (1, 3, 28, 157, 1589)
NAMES = ('Mark Evans', 'Jack Wallside', 'Daniel Hatch', 'Byron Love', 'Nathan Swift')


def emit_dynamic_removals(program):
    """132 bounded slots cover the entire measured native player database.

    The host fills these with owned units before the event is allowed to run;
    empty slots are guarded, so reserve players cannot leak into a friendly.
    """
    from ssd import expression
    for index in range(132):
        placeholder = 0x400000 + index
        program.emit(0x6008, expression(0x7002, expression(0x7003, placeholder, 0)))
        branch = program.emit(0x6001, 1, 0)
        program.emit(0x403F, placeholder)
        program.end(branch)


def isolate_first_chapter_roster(ssd):
    """Disable the original chapter's explicit twelve-player rebuild.

    Retain instruction IDs and references while replacing native remove/add
    calls with a zero-frame wait, then registers the five requested players
    through the original add command. Recompute sizes because excess
    three-argument add rows become one-argument
    waits; text count, bindings and engine callback order are preserved.
    """
    rows, header = read_ssd(ssd)
    remove_rows = rows[2584:2596]
    add_rows = rows[2596:2608]
    expected_units = (1, 2, 3, 4, 5, 6, 7, 8, 9, 1097, 11, 12)
    if len(add_rows) != 12 or any(r.opcode != 0x403F or r.types != [1] or r.args != [i+1]
            for i, r in enumerate(remove_rows)):
        raise ValueError('Unexpected chapter player-removal block')
    if any(r.opcode != 0x403E or r.types != [1, 1, 1] or r.args != [unit, 1, i+1]
            for i, (r, unit) in enumerate(zip(add_rows, expected_units))):
        raise ValueError('Unexpected chapter player-addition block')
    for row in remove_rows+add_rows:
        row.opcode = 0x3002
        row.types = [1]
        row.args = [0]
    for i, (row, unit) in enumerate(zip(add_rows, ROSTER)):
        row.opcode = 0x403E
        row.types = [1, 1, 1]
        row.args = [unit, 1, i+1]
    body = b''.join(row.encode() for row in rows)
    updated = bytearray(ssd[:32])
    struct.pack_into('<I', updated, 8, 32+len(body)+header['text_size'])
    struct.pack_into('<I', updated, 16, len(body))
    result = bytes(updated)+body
    read_ssd(result)
    return result


def prepare_team(rom, roster=ROSTER):
    """Return one exact resource edit and static evidence for the new-game team."""
    if sha(rom.data) != ORIGINAL_SHA256:
        raise ValueError('Unsupported original ROM for team initialization')
    if len(roster) != 5 or len(set(roster)) != 5 or any(not 0 < n < 0x8000 for n in roster):
        raise ValueError('Expected five distinct valid unit IDs')
    data = rom.data[slice(*rom.files[TEAM_PATH])]
    index = rom.data[slice(*rom.files[INDEX_PATH])]
    if index[:16] != b'PackNum 20080626' or struct.unpack_from('<H', index, 18)[0] != 3:
        raise ValueError('Unexpected fixed-record team index')
    if struct.unpack_from('<I', index, 28)[0] != 320 or struct.unpack_from('<I', index, 48)[0] != 1:
        raise ValueError('Unexpected early-game team key/record size')
    before = data[:320]
    if before[:7] != b'Raimon\0' or struct.unpack_from('<H', before, 0x40)[0] != 1:
        raise ValueError('Unexpected original initial team')
    if any(struct.unpack_from('<H', before, 0x40+i*8)[0] for i in range(1, 32)):
        raise ValueError('Original initial roster no longer contains only Mark')
    after = bytearray(before)
    for i, unit in enumerate(roster):
        pos = 0x40+i*8
        struct.pack_into('<H', after, pos, unit)
        after[pos+2] = i+1   # party slot (native loader supports five)
        after[pos+3] = i+1   # preserve original matching formation order convention
        after[pos+4:pos+8] = b'\0'*4  # base level 1 + delta 0; remaining flags unchanged zero
    # Validate named units and Nathan's actual Empereurs noirs team association.
    unitbase = rom.data[slice(*rom.files['data_iz/logic/fr/unitbase.dat'])]
    unitno = rom.data[slice(*rom.files['data_iz/logic/fr/unitno.dat'])]
    for native_id, record, wanted in zip(ROSTER, BASE_RECORDS, NAMES):
        observed = unitbase[record*96:record*96+32].split(b'\0')[0].decode('ascii')
        if observed != wanted:
            raise ValueError('Unexpected named player mapping')
        if struct.unpack_from('<H', unitno, record*2)[0] != native_id or struct.unpack_from('<H', unitbase, record*96+66)[0] != native_id:
            raise ValueError('Native unit ID differs from unitno/base record mapping')
    if unitbase[1589*96+65] != 41:
        raise ValueError('Nathan is not associated with team 41')
    team_index = rom.data[slice(*rom.files['data_iz/logic/fr/team.pkh'])]
    team_data = rom.data[slice(*rom.files['data_iz/logic/fr/team.pkb'])]
    keys = struct.unpack_from('<'+'I'*((len(team_index)-48)//4), team_index, 48)
    dark_name = team_data[keys.index(41)*320:keys.index(41)*320+32].split(b'\0')[0]
    if dark_name != b'Empereurs noirs':
        raise ValueError('Unexpected team 41 identity')
    edits = [{'path': TEAM_PATH, 'resource_sha256': sha(data), 'offset': 0,
              'before_hex': before.hex(), 'after_hex': after.hex()}]
    # The preserved native first chapter subsequently rebuilds Raimon from the
    # general library. Match both templates, otherwise that rebuild restores the
    # original twelve-player squad after the initial one-player new-game team.
    general_path = 'data_iz/logic/fr/team.pkb'
    general = rom.data[slice(*rom.files[general_path])]
    general_before = general[:320]
    if general_before[:7] != b'Raimon\0' or [struct.unpack_from('<H', general_before, 0x40+i*8)[0] for i in range(12)] != list(range(1, 13)):
        raise ValueError('Unexpected general-library Raimon roster')
    general_after = bytearray(general_before)
    for i in range(32):
        pos = 0x40+i*8
        struct.pack_into('<H', general_after, pos, roster[i] if i < 5 else 0)
        general_after[pos+2] = i+1 if i < 5 else 0
        # Slot/order fields for empty rows remain in their original convention.
        general_after[pos+4:pos+8] = b'\0'*4
    edits.append({'path': general_path, 'resource_sha256': sha(general), 'offset': 0,
                  'before_hex': general_before.hex(), 'after_hex': general_after.hex()})
    evidence = {'templates': [TEAM_PATH, general_path], 'team_key': 1, 'base_level': 1,
                'level_deltas': [0]*5, 'units': list(roster),
                'unitbase_records': list(BASE_RECORDS),
                'nathan_variant': 'Empereurs noirs (team 41)',
                'runtime_verified': False}
    return edits, evidence


def inspect_party_memory(memory, base_address=0x02000000):
    """Read occupied player records from an ARM9 RAM dump, without altering it.

    BEBF native database: 020E0300; record stride FC; ID64, levelAA, flagsF0.
    Team membership bit15 in field42 distinguishes native opponent records.
    Preserve raw flags in the report rather than assuming every occupied record
    belongs to the user's team.
    """
    start = 0x020E0300-base_address
    if start < 0 or start+132*0xFC > len(memory):
        raise ValueError('Dump does not cover the native player database')
    result = []
    for i in range(132):
        pos = start+i*0xFC
        flags = struct.unpack_from('<H', memory, pos+0xF0)[0]
        if flags & 1:
            result.append({'record': i, 'address': base_address+pos,
                'unit': struct.unpack_from('<H', memory, pos+0x64)[0],
                'level': memory[pos+0xAA], 'flags': flags,
                'team_field': struct.unpack_from('<H', memory, pos+0x42)[0]})
    return result
