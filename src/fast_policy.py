"""Bounded deterministic UI actions for measured native BEBF screens.

The screen observation is produced inside the emulator worker. It must never
be fabricated from an LLM answer. Tactical choices and unknown screens fall
back to the model. A three-action repeat guard bounds a failed native click.
"""

SIMPLE_SCREENS = {
    'formation_overview','formation_details','kickoff_ready','goal_replay',
    'stylus_prompt','halftime','kickoff_pass','native_pitch_dialogue',
}


def fast_decision(state, history):
    """Return a validated-shape action for a known single-choice UI, else None."""
    screen = state.get('screen',{})
    tactical = state.get('tactical',{})
    if (screen.get('name') == 'unknown' and
            (state.get('phase') in ('starting','loading') or
             (state.get('phase') == 'playing' and tactical.get('source') == 'native_memory'
              and tactical.get('reason') == 'Native football roster is incomplete'))):
        decision = {'intent':'act','reason':'Attendre le chargement natif','frames':120,
                    'keys':[],'touch':None,'path':[]}
        if not _repeated(decision,history):
            return decision
        return None
    if (screen.get('source') != 'measured_frame_signature' or
            screen.get('name') not in SIMPLE_SCREENS):
        return None
    actions = screen.get('actions',[])
    if len(actions) != 1:
        return None
    action = actions[0]
    decision = {'intent':'act', 'reason':action['name'], 'frames':action['frames'],
                'keys':list(action['keys']), 'touch':action['touch'], 'path':[]}
    if _repeated(decision,history):
        return None
    return decision


def _repeated(decision, history):
    fields = ('intent','frames','keys','touch','path')
    return len(history) >= 3 and all(all(previous.get(key) == decision[key] for key in fields)
                                    for previous in history[-3:])
