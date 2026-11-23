"""Compact, provenance-preserving state for the hybrid player.

An occupied roster is not a tactical observation. Text-only inference requires
an explicitly validated tactical decoder, a known control surface and current
legal actions. Unknown fields never become fabricated positions or scores.
"""


def text_actions(state):
    screen = state.get('screen', {})
    if (screen.get('source') == 'measured_frame_signature'
            and screen.get('name') != 'unknown' and len(screen.get('actions', [])) > 1):
        return screen['actions']
    tactical = state.get('tactical', {})
    if (state.get('phase') == 'playing'
            and tactical.get('ready_for_text') is True
            and bool(tactical.get('source'))
            and bool(tactical.get('legal_actions'))):
        return tactical['legal_actions']
    return []


def text_ready(state):
    return state.get('phase') not in ('result', 'booting', 'loading') and bool(text_actions(state))


def compact_state(state):
    """Drop dialogue scripts, full roster IDs and duplicated fixture metadata."""
    result = {key: state[key] for key in ('phase', 'native_counter', 'screen', 'tactical',
                                        'native_result', 'result', 'result_source')
              if key in state and state[key] is not None}
    fixture = state.get('fixture')
    if fixture:
        result['teams'] = {key: fixture[key] for key in ('home', 'away') if key in fixture}
    if isinstance(result.get('tactical'),dict):
        tactical = result['tactical']
        # Keep actionable measurements, not the address/flag audit for every
        # occupied database record. The full readback stays in observations.
        reduced = {key:value for key,value in tactical.items()
                   if key in ('source','ready_for_text','ball','possession','score','clock',
                              'controlled_player','legal_actions','unavailable','coordinate_system')}
        reduced['coordinate_system'] = 'native_world_not_touchscreen'
        if isinstance(reduced.get('ball'),dict):
            reduced['ball'] = {key:value for key,value in reduced['ball'].items() if key in ('x','y')}
        if tactical.get('positions'):
            reduced['positions'] = [{key:value for key,value in player.items()
                                     if key in ('unit','side','x','y')}
                                    for player in tactical['positions']]
        result['tactical'] = reduced
    return result


def compact_history(history):
    """Keep recent actual inputs, without model explanations or internal tags."""
    return [{key: row[key] for key in ('frames', 'keys', 'touch', 'path') if key in row}
            for row in history[-4:]]
