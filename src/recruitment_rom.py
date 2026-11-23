"""Fixed-size recruitment resources for the French BEBF Club ROM."""

import ctypes
import struct

from nds import patch, sha

ROOT = 'data_iz/logic/fr/'
COUNT = 2400
FIRST_RESERVED = 2064
FIRST_RECRUIT_ID = 2931
MAX_TEAM_RECRUITS = 11
RESOURCES = {
    ROOT + 'unitbase.dat': 96,
    ROOT + 'unitno.dat': 2,
    ROOT + 'unitstat.dat': 80,
    'data_iz/logic01/fr/unitstat.dat': 80,
    ROOT + 'unitbase.STR': 128,
}


def encode_name(name):
    """Use the printable ASCII subset verified by the native name renderer."""
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 31:
        raise ValueError('Le nom doit contenir entre 1 et 31 caractères.')
    name = name.strip()
    if any(not 32 <= ord(char) <= 126 for char in name):
        raise ValueError('Le nom de la recrue doit utiliser des caractères ASCII imprimables.')
    return name.encode('ascii').ljust(32, b'\0')


def recruitment_squad(roster, team, drafts):
    recruits = [(FIRST_RECRUIT_ID + index, draft['level']) for index, draft in enumerate(drafts)
                if draft['team_id'] == team]
    squad = [(unit, 30) for unit in roster if unit]
    start = MAX_TEAM_RECRUITS - len(recruits)
    squad[start:start] = recruits
    return squad[:16]


def build_recruitment_rom(rom, *, expected_sha256, drafts, arena=False):
    """Clone the selected native units into successive reserved rows."""
    if sha(rom.data) != expected_sha256 or rom.data[12:16] != b'BEBF' or rom.data[30] != 0:
        raise ValueError('Version de la ROM Club incompatible avec le recrutement.')
    resources = {}
    for path, size in RESOURCES.items():
        data = rom.data[slice(*rom.files[path])]
        if len(data) != COUNT * size:
            raise ValueError(f'Taille inattendue de la ressource {path}.')
        resources[path] = data
    ids = struct.unpack(f'<{COUNT}H', resources[ROOT + 'unitno.dat'])
    base = resources[ROOT + 'unitbase.dat']
    if (ids[0] != 0 or ids[FIRST_RESERVED - 1] != FIRST_RECRUIT_ID - 1
            or any(ids[FIRST_RESERVED:]) or len(set(ids[:FIRST_RESERVED])) != FIRST_RESERVED
            or any(unit != struct.unpack_from('<H', base, row * 96 + 66)[0]
                   for row, unit in enumerate(ids))):
        raise ValueError('La cartographie native des identifiants a changé.')
    edits = []
    for index, draft in enumerate(drafts):
        unit = FIRST_RECRUIT_ID + index
        reserved = FIRST_RESERVED + index
        template_unit = draft['template_unit']
        if type(template_unit) is not int or template_unit <= 0 or template_unit not in ids:
            raise ValueError('Identifiant du modèle natif inconnu.')
        source = ids.index(template_unit)
        names = encode_name(draft['name']) + encode_name(draft['short_name'])
        for path, size in RESOURCES.items():
            data = resources[path]
            offset = reserved * size
            before = data[offset:offset + size]
            after = bytearray(data[source * size:(source + 1) * size])
            if path.endswith('unitno.dat'):
                struct.pack_into('<H', after, 0, unit)
            elif path.endswith('unitbase.dat'):
                after[:64] = names
                struct.pack_into('<H', after, 66, unit)
                struct.pack_into('<H', after, 94, reserved)
            elif path.endswith('.STR'):
                after = b'Recrue du Club.'.ljust(size, b'\0')
            if before != after:
                edits.append({'path': path, 'resource_sha256': sha(data), 'offset': offset,
                              'before_hex': before.hex(), 'after_hex': after.hex()})
    if arena:
        path = ROOT + 'team.pkb'
        teams = rom.data[slice(*rom.files[path])]
        index = rom.data[slice(*rom.files[ROOT + 'team.pkh'])]
        keys = [struct.unpack_from('<I', index, 48 + i * 4)[0] for i in range(len(teams) // 320)]
        for team in dict.fromkeys(draft['team_id'] for draft in drafts):
            # Match 500 uses the isolated Raimon roster under native key 70.
            key = 70 if team == 1 else team
            recruits = [FIRST_RECRUIT_ID + i for i, draft in enumerate(drafts) if draft['team_id'] == team]
            for slot, unit in enumerate(recruits, MAX_TEAM_RECRUITS - len(recruits)):
                offset = keys.index(key) * 320 + 64 + slot * 8
                edits.append({'path': path, 'resource_sha256': sha(teams), 'offset': offset,
                              'before_hex': teams[offset:offset + 2].hex(),
                              'after_hex': struct.pack('<H', unit).hex()})
    return patch(rom, {'rom_sha256': expected_sha256, 'edits': edits})


def refresh_unit_index(pointer, memory, original, rebuilt, previous_count=0):
    """Refresh the one measured copy retained by a vanilla Club save state."""
    from arena_bridge import occurrences

    start, end = original.files[ROOT + 'unitno.dat']
    previous = bytearray(original.data[start:end])
    for index in range(previous_count):
        struct.pack_into('<H', previous, (FIRST_RESERVED + index) * 2, FIRST_RECRUIT_ID + index)
    positions = list(occurrences(memory, bytes(previous)))
    if len(positions) != 1:
        raise ValueError('La table des joueurs ne peut pas être restaurée dans cet état.')
    ctypes.memmove(pointer + positions[0], rebuilt[start:end], end - start)
