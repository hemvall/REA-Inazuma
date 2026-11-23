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
                if draft.get('team_id') == team]
    squad = [(unit, 30) for unit in roster if unit]
    start = MAX_TEAM_RECRUITS - len(recruits)
    squad[start:start] = recruits
    return squad[:16]


def build_recruitment_rom(rom, *, expected_sha256, drafts, arena=False):
    """Clone the selected native units into successive reserved rows."""
    from arena_graphics import add_graphics
    from souls_recruitment import source_players

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
    imported = source_players() if any('souls_unit' in draft for draft in drafts) else {}
    if imported and not arena:
        raise ValueError('Le joueur personnalisé est réservé à Inazuma FC.')
    if imported:
        field_hashes = next(iter(imported.values()))['field_hashes']
        if any(sha(rom.data[slice(*rom.files[path])]) != digest for path, digest in field_hashes.items()):
            raise ValueError('Cette version de Souls 2 utilise des archives de sprites de terrain différentes.')
    edits = []
    imported_graphics = {}
    for index, draft in enumerate(drafts):
        unit = FIRST_RECRUIT_ID + index
        reserved = FIRST_RESERVED + index
        souls = imported.get(draft.get('souls_unit'))
        template_unit = 7 if souls else draft.get('template_unit')
        model = 3000 + index
        if souls:
            imported_graphics[model] = souls
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
                if souls:
                    source_base = souls['base']
                    # Souls 2 Extreme shares the French ROM's field sprite archives.
                    # Copy the body, head, palette and skin references from its player row.
                    after[0x46:0x52] = source_base[0x46:0x52]
                    for field in (0x40, 0x52, 0x54, 0x55, 0x5A):
                        after[field] = source_base[field]
                    struct.pack_into('<H', after, 0x44, model)
                after[:64] = names
                struct.pack_into('<H', after, 66, unit)
                struct.pack_into('<H', after, 94, reserved)
            elif path.endswith('.STR'):
                after[:] = b'Recrue du Club.'.ljust(size, b'\0')
            elif souls and path.endswith('unitstat.dat'):
                after[:] = souls['stats' if path.startswith(ROOT) else 'match_stats']
            if before != after:
                edits.append({'path': path, 'resource_sha256': sha(data), 'offset': offset,
                              'before_hex': before.hex(), 'after_hex': after.hex()})
    if arena:
        path = ROOT + 'team.pkb'
        teams = rom.data[slice(*rom.files[path])]
        index = rom.data[slice(*rom.files[ROOT + 'team.pkh'])]
        keys = [struct.unpack_from('<I', index, 48 + i * 4)[0] for i in range(len(teams) // 320)]
        for team in dict.fromkeys(draft['team_id'] for draft in drafts if 'team_id' in draft):
            # Match 500 uses the isolated Raimon roster under native key 70.
            key = 70 if team == 1 else team
            recruits = [FIRST_RECRUIT_ID + i for i, draft in enumerate(drafts) if draft.get('team_id') == team]
            for slot, unit in enumerate(recruits, MAX_TEAM_RECRUITS - len(recruits)):
                offset = keys.index(key) * 320 + 64 + slot * 8
                edits.append({'path': path, 'resource_sha256': sha(teams), 'offset': offset,
                              'before_hex': teams[offset:offset + 2].hex(),
                              'after_hex': struct.pack('<H', unit).hex()})
    rebuilt = patch(rom, {'rom_sha256': expected_sha256, 'edits': edits})
    return add_graphics(rebuilt, imported_graphics) if imported_graphics else rebuilt


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
