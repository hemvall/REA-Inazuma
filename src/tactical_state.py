"""Read-only, version-gated BEBF football state from native ARM9 RAM.

Evidence is local disassembly plus retained ``build/research/*.ram`` snapshots.
ARM9 02062E94 reads roster+E8 and compares it with ball 020C4940; 02062E54
uses the first two signed words as planar coordinates. Movement arithmetic uses
12 fractional bits. Roster+EC is a different AI/movement state, not the current
position. Native owner lookup at 02131E48 calls 02035970, which indexes the
pointer table at 020E84F0; an owner is NOT an index into fixed roster records.

In field.ram, owner 24 resolves to unit 189 (Demeter): its position is
(304.13, 304.64), ball is (304.13, 314.64), consistent with the retained duel
image. These observations establish positions and possession, not a world-to-
touch projection, camera transform or controlled player. Score and clock are
corroborated by a separate native goal replay: 0-0 -> 0-1, Demeter at 15:22.
The retained evidence is in build/research/score-clock/. The clock is native
ticks/30, not an inferred total elapsed time across periods.
"""
import struct

from scene_team import inspect_party_memory

RAM_BASE = 0x02000000
RAM_SIZE = 4 * 1024 * 1024
ROSTER_BASE = 0x020E0300
ROSTER_STRIDE = 0xFC
POSITION_BASE = 0x0212BEA8
POSITION_STRIDE = 0x20
OWNER_TABLE = 0x020E84F0
BALL_BASE = 0x020C4940
CLOCK_BASE = 0x020CA380
SCORE_BASE = 0x020CA408
SCORE_SIGNATURE = bytes.fromhex('0800a0e14f5e00eb000050e320029f058810d0058900d00514029f158910d015')
SCALE = 4096

# Small native instruction signatures prevent applying this mapping to shifted
# code or another game revision. ArenaBridge additionally locks the ROM SHA256.
SIGNATURES = {
    0x02062E94: bytes.fromhex('e81091e504209fe504c09fe51cff2fe1'),
    0x02035970: bytes.fromhex('010180e0020980e2f00190e51eff2fe1'),
}


def _word(memory, address, fmt='<I'):
    return struct.unpack_from(fmt, memory, address - RAM_BASE)[0]


def _point(memory, address):
    x, y = struct.unpack_from('<ii', memory, address - RAM_BASE)
    # A corruption guard only; this is deliberately NOT a claimed pitch size.
    if not (-4096 * SCALE <= x <= 4096 * SCALE and
            -4096 * SCALE <= y <= 4096 * SCALE):
        return None
    return {'world_fixed': {'x': x, 'y': y},
            'x': round(x / SCALE, 4), 'y': round(y / SCALE, 4)}


def extract_tactical_state(memory, phase, players=None):
    """Return only verified fields; unknown input mappings retain vision fallback.

    ``players`` optionally reuses ``inspect_party_memory`` rows from the same
    snapshot. Every supplied record is revalidated against the bytes here.
    ``ready_for_text`` remains false until legal actions/touch mapping exist.
    """
    result = {
        'source': 'native_memory', 'version': 'BEBF', 'ready_for_text': False,
        'valid': False, 'phase': phase, 'coordinate_scale': SCALE,
        'positions': [], 'ball': None, 'possession': None,
        'controlled_player': None, 'score': None, 'clock': None,
        'legal_actions': [],
        'unavailable': ['positions', 'ball', 'possession', 'controlled_player',
                        'world_to_touch', 'score', 'clock', 'legal_actions'],
        'evidence': {'position': 'roster+0xE8 -> signed FX12 x,y',
                     'ball': '0x020C4940 +0,+4',
                     'possession': '0x020C4940+0x48 -> 0x020E84F0 pointer table'},
    }
    if len(memory) != RAM_SIZE:
        result['reason'] = 'Unsupported ARM9 RAM size'
        return result
    if any(memory[address-RAM_BASE:address-RAM_BASE+len(signature)] != signature
           for address, signature in SIGNATURES.items()):
        result['reason'] = 'Native instruction signature mismatch'
        return result
    if phase not in ('playing', 'halftime', 'result'):
        result['reason'] = 'Football state is not active'
        return result
    observed = inspect_party_memory(memory)
    actual = {row['record']: row for row in observed}
    rows = observed if players is None else players
    position_rows = []
    by_address = {}
    for row in rows:
        current = actual.get(row.get('record'))
        if current is None or current != row:
            continue
        address = current['address']
        # Bit 3 is required by native football-roster queries (02131F78).
        if not current['flags'] & 8:
            continue
        side = memory[address - RAM_BASE + 0xB6]
        order = memory[address - RAM_BASE + 0xB7]
        if side not in (0, 1) or not 1 <= order <= 11:
            continue
        pointer = _word(memory, address + 0xE8)
        if pointer != POSITION_BASE + current['record'] * POSITION_STRIDE:
            continue
        point = _point(memory, pointer)
        if point is None:
            continue
        entry = {'record': current['record'], 'unit': current['unit'],
                 'side': 'home' if side == 0 else 'away',
                 'formation_slot': order, **point}
        position_rows.append(entry)
        by_address[address] = entry
    # At least two sides must be present; stale/partial roster initialization
    # must not be reported as a complete match-state observation.
    if {p['side'] for p in position_rows} != {'home', 'away'}:
        result['reason'] = 'Native football roster is incomplete'
        return result
    result['positions'] = position_rows
    result['unavailable'].remove('positions')
    ball = _point(memory, BALL_BASE)
    if ball is None:
        result['reason'] = 'Ball coordinate guard failed'
        return result
    result['ball'] = ball
    result['unavailable'].remove('ball')
    owner = _word(memory, BALL_BASE + 0x48, '<i')
    if owner == -1:
        result['possession'] = {'side': 'none', 'unit': None, 'native_index': -1}
    elif 0 <= owner < 132:
        address = _word(memory, OWNER_TABLE + owner * 4)
        player = by_address.get(address)
        if player is not None:
            result['possession'] = {'side': player['side'], 'unit': player['unit'],
                                    'record': player['record'], 'native_index': owner}
    if result['possession'] is not None:
        result['unavailable'].remove('possession')
    result['valid'] = result['possession'] is not None
    if memory[0x0206ABDC-RAM_BASE:0x0206ABDC-RAM_BASE+len(SCORE_SIGNATURE)] == SCORE_SIGNATURE:
        home, away = struct.unpack_from('<BB',memory,SCORE_BASE-RAM_BASE)
        if home <= 99 and away <= 99:
            result['score'] = {'home':home,'away':away}
            result['unavailable'].remove('score')
        ticks = _word(memory,CLOCK_BASE)
        mirror = _word(memory,CLOCK_BASE+4)
        if ticks == mirror and ticks <= 200*60*30:
            result['clock'] = {'ticks':ticks,'ticks_per_second':30,'seconds':ticks//30,
                               'period_raw':memory[0x020CA3FF-RAM_BASE]}
            result['unavailable'].remove('clock')
        result['evidence'].update(score='0x020CA408,+1 -> home,away; native 0-1 goal replay',
                                  clock='0x020CA380,+4 mirror; ticks/30; display may lag one second')
    result['reason'] = ('World coordinates available; touch projection and controlled player are unverified'
                        if result['valid'] else 'Native ball owner did not resolve to an active player')
    return result
