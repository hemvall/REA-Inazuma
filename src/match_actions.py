"""Semantic commands backed by measured arena transitions."""

TRANSITIONS = {
    'versus_intro': 'formation.open',
    'formation_overview': 'formation.continue',
    'formation_details': 'formation.back',
    'kickoff_ready': 'kickoff.start',
    'restart_ready': 'restart.continue',
    'kickoff_pass': 'kickoff.pass_left',
    'kickoff_pass_forward': 'kickoff.pass_forward',
    'native_pitch_dialogue': 'dialogue.continue',
    'pitch_dialogue_confirm': 'dialogue.continue',
    'goal_replay': 'replay.continue',
    'stylus_prompt': 'tutorial.continue',
    'halftime': 'halftime.continue',
    'shot_block_menu': 'shot.block_special',
}

DUEL_ACTION_IDS = {
    'attack_duel': ('duel.dribble', 'duel.feint'),
    'attack_duel_dodge': ('duel.dribble', 'duel.dodge'),
    'defence_duel': ('duel.tackle', 'duel.block'),
    'defence_duel_contact': ('duel.tackle', 'duel.contact'),
    'keeper_duel': ('keeper.punch', 'keeper.catch'),
}


def legal_commands(match):
    if not match.get('fixture') or match['phase'] == 'result':
        return {}
    if match['phase'] == 'idle' and match['native_counter'] == 4:
        return {'match.start': None}
    if match['phase'] == 'dialogue':
        return {'dialogue.continue': {'frames': 3, 'keys': ['A'], 'touch': None}}
    screen = match['screen']
    if screen['source'] != 'measured_frame_signature':
        return {}
    if match['phase'] == 'playing':
        duel = DUEL_ACTION_IDS.get(screen['name'])
        if duel and len(screen['actions']) == 2:
            return dict(zip(duel, reversed(screen['actions'])))
        tactical = match['tactical']
        possession = tactical['possession'] or {}
        if screen['name'] == 'pass_prompt' and possession.get('side') == 'home':
            return {'pass.forward': screen['actions'][0]}
        score = tactical['score']
        if (screen['name'] == 'goal_replay_technique' and score and any(score.values())
                and possession.get('side') == 'none'):
            return {'replay.continue': screen['actions'][0]}
    action_id = TRANSITIONS.get(screen['name'])
    if action_id and len(screen['actions']) == 1:
        return {action_id: screen['actions'][0]}
    return {}


def observe_match(match, frame, revision):
    tactical = match['tactical']
    return {
        'frame': frame, 'revision': revision, 'phase': match['phase'],
        'screen': match['screen']['name'],
        'score': tactical['score'], 'clock': tactical['clock'],
        'possession': tactical['possession'], 'controlled_player': tactical['controlled_player'],
        'legal_actions': [{'id': action_id} for action_id in legal_commands(match)],
        'result': match['result'], 'native_result': match['native_result'],
        'result_source': match['result_source'],
    }
