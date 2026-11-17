"""Patch only the four-player opponent template used by native challenge 35."""
import struct
from nds import sha

TEAM_PATH = 'data_iz/logic/fr/team.pkb'
INDEX_PATH = 'data_iz/logic/fr/team.pkh'
TEAM_KEY = 70
ORIGINAL_UNITS = (2591, 2533, 2548, 2572)


def prepare_opponents(rom, config):
    data = rom.data[slice(*rom.files[TEAM_PATH])]
    index = rom.data[slice(*rom.files[INDEX_PATH])]
    if struct.unpack_from('<I', index, 28)[0] != 320:
        raise ValueError('Unexpected opponent template stride')
    keys = struct.unpack_from('<'+'I'*((len(index)-48)//4), index, 48)
    offset = keys.index(TEAM_KEY)*320
    before = data[offset:offset+320]
    units = tuple(struct.unpack_from('<H', before, 64+i*8)[0] for i in range(4))
    if units != ORIGINAL_UNITS or before[:4] != b'???\0':
        raise ValueError('Unexpected original challenge opponents')
    games = rom.data[slice(*rom.files['data_iz/logic/games.dat'])]
    if struct.unpack_from('<H', games, config['native_match_id']*48)[0] != TEAM_KEY:
        raise ValueError('Challenge no longer points at opponent team 70')
    roster = config['opponents']['players']
    if len(roster) != 4 or len({p['unit'] for p in roster}) != 4:
        raise ValueError('The native challenge needs four distinct opponents')
    unitbase = rom.data[slice(*rom.files['data_iz/logic/fr/unitbase.dat'])]
    unitno = rom.data[slice(*rom.files['data_iz/logic/fr/unitno.dat'])]
    after = bytearray(before)
    name = config['opponents']['name'].encode('ascii')
    if not 0 < len(name) < 32:
        raise ValueError('Opponent team name exceeds its native field')
    after[:32] = name+bytes(32-len(name))
    for i, player in enumerate(roster):
        record = player['base_index']
        observed = unitbase[record*96:record*96+32].split(b'\0')[0].decode('ascii')
        if observed != player['full_name'] or struct.unpack_from('<H', unitno, record*2)[0] != player['unit']:
            raise ValueError('Opponent identity does not match the original ROM')
        struct.pack_into('<H', after, 64+i*8, player['unit'])
        after[68+i*8] = 0  # Same native level-one baseline as the player squad.
    return [{'path': TEAM_PATH, 'resource_sha256': sha(data), 'offset': offset,
             'before_hex': before.hex(), 'after_hex': after.hex()}], {
        'team_key': TEAM_KEY, 'offset': offset, 'size': 320,
        'name': config['opponents']['name'], 'players': roster,
        'runtime_verified': False}
