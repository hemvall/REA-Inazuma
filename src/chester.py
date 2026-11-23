"""Confirmed match events and optional editorial variation for Chester."""
from collections import Counter, deque
import re
import time


ACTION_SCREENS = {
    'attack_duel': 'attack_duel', 'attack_duel_dodge': 'attack_duel',
    'defence_duel': 'defence_duel', 'defence_duel_contact': 'defence_duel',
    'shot_block_menu': 'shot', 'keeper_duel': 'shot',
}

ACTION_LINES = {
    'attack_duel': ('Le porteur provoque son défenseur ! Est-ce qu’il va trouver le passage ?',
                    'Le voilà en un contre un ! À lui de faire la différence.'),
    'defence_duel': ('Le défenseur ferme le passage ! Il va falloir choisir le bon moment pour intervenir.',
                     'Duel défensif ! Le porteur va devoir se défaire du marquage.'),
    'shot': ('Attention, le tir part ! La défense peut encore intervenir.',
             'Ça frappe ! Tout se joue maintenant devant le but.'),
    'turnover': ('{team} récupère le ballon ! Le jeu peut repartir dans l’autre sens.',
                 'Changement de possession ! À {team} de profiter de cette récupération.'),
    'handoff': ('Le ballon change de porteur, et {team} garde la maîtrise.',
                '{team} trouve un autre porteur et conserve le ballon.'),
    'resume': ('C’est reparti après la pause ! Voyons qui va prendre l’initiative.',),
    'halftime': ('C’est la mi-temps ! {score}',),
}


class MatchCommentary:
    def __init__(self):
        self.sequence = 0
        self.epoch = 0
        self.fixture = None
        self.events = deque(maxlen=12)
        self.reset()

    def reset(self, restored=False):
        self.epoch += 1
        self.events.clear()
        self.started = self.finished = False
        self.score = None
        self.possession = None
        self.phase = None
        self.halftime_seen = self.resumed = False
        self.calls = Counter()
        self.last_action = None
        self.last_action_frame = -120
        self.baseline = restored

    def observe(self, match, observation, teams):
        fixture = match['fixture']
        identity = fixture['id'] if fixture else None
        if identity != self.fixture:
            self.fixture = identity
            if not self.baseline:
                self.reset()
        if not fixture:
            self.baseline = False
            return

        phase = observation['phase']
        score = observation['score']
        frame = observation['frame']
        screen = observation.get('screen')
        action = ACTION_SCREENS.get(screen)
        old_phase, self.phase = self.phase, phase
        possession = observation.get('possession') or {}
        side = possession.get('side')
        player = possession.get('record', possession.get('unit'))
        holder = (side, player) if side in ('home', 'away') and player is not None else None
        old_holder = self.possession
        if holder is not None or phase != 'playing' or screen == 'restart_ready':
            self.possession = holder
        final = phase == 'result' and observation['result_source'] in ('native_callback', 'native_final_screen')
        if self.baseline:
            self.started = phase in ('playing', 'halftime', 'result')
            self.finished = final
            self.score = score
            self.last_action = action
            self.last_action_frame = frame
            self.halftime_seen = phase == 'halftime'
            self.baseline = False
            return

        def emit(kind, side=None, result_score=None):
            home = teams[fixture['home']]['name']
            away = teams[fixture['away']]['name']
            score_text = (f'{home} {result_score["home"]}, {away} {result_score["away"]}.'
                          if result_score else '')
            if kind == 'goal':
                scorer = home if side == 'home' else away
                difference = result_score[side] - result_score['away' if side == 'home' else 'home']
                call = ('Égalisation !' if difference == 0 else 'Le match bascule !' if difference == 1 else
                        'L’écart se réduit !' if difference < 0 else 'L’écart se creuse !')
                text = f'Et ça rentre pour {scorer} ! {call} {score_text}'
            elif kind == 'result':
                text = (f'Score final. {score_text}' if score_text else
                        'C’est terminé, le résultat officiel est à l’écran.')
            elif kind == 'kickoff':
                text = f'C’est parti ! {home} et {away} entrent dans leur match.'
            else:
                lines = ACTION_LINES[kind]
                text = lines[self.calls[kind] % len(lines)].format(
                    team=home if side == 'home' else away, score=score_text).strip()
                if kind in ('turnover', 'handoff'):
                    team = teams[fixture[side]]
                    name = team.get('roster_names', {}).get(possession.get('unit'))
                    if name:
                        text = (f'{name} récupère pour {team["name"]} ! Le jeu peut repartir dans l’autre sens.'
                                if kind == 'turnover' else f'Le ballon est maintenant à {name}. {team["name"]} conserve.')
            self.sequence += 1
            self.calls[kind] += 1
            self.events.append({
                'id': self.sequence, 'kind': kind, 'side': side, 'score': result_score,
                'home': fixture['home'], 'away': fixture['away'],
                'frame': observation['frame'], 'at': time.time(), 'text': text,
                'match_score': score, 'clock_seconds': (observation.get('clock') or {}).get('seconds'),
            })

        if final and not self.finished:
            self.finished = True
            emit('result', result_score=score)
        if self.finished or phase not in ('playing', 'halftime'):
            return
        if not self.started:
            self.started = True
            emit('kickoff')
        goal = False
        if score is not None and self.score is not None:
            for side, opponent in (('home', 'away'), ('away', 'home')):
                if score[side] == self.score[side] + 1 and score[opponent] == self.score[opponent]:
                    emit('goal', side, score)
                    goal = True
        if score is not None and (self.score is None or all(score[side] >= self.score[side] for side in ('home', 'away'))):
            self.score = score
        if phase == 'halftime' and not self.halftime_seen:
            self.halftime_seen = True
            emit('halftime', result_score=score)
        elif phase == 'playing' and old_phase == 'halftime' and not self.resumed:
            self.resumed = True
            emit('resume')
        elif phase == 'playing' and not goal:
            if action and (action != self.last_action or frame - self.last_action_frame >= 120):
                emit(action)
            elif (not action and holder and old_holder and holder != old_holder
                  and screen not in ('restart_ready', 'kickoff_ready', 'goal_replay',
                                     'goal_replay_video', 'goal_replay_technique', 'scoreboard_transition')):
                emit('turnover' if holder[0] != old_holder[0] else 'handoff', holder[0])
                self.last_action = None
        if action:
            self.last_action = action
            self.last_action_frame = frame

    def snapshot(self):
        return {'epoch': self.epoch, 'cursor': self.sequence, 'events': list(self.events)}


def generate_reaction(agent, kind, previous, *, match_context):
    schema = {
        'type': 'object', 'additionalProperties': False, 'required': ['reaction'],
        'properties': {'reaction': {'type': 'string'}},
    }
    prompt = (
        'Écris une seule phrase originale de direct football, dans l’esprit de Chester Horse Junior : '
        'observateur de terrain, débit vif, précis, enthousiaste sur les temps forts. '
        'Réagis au placement, au duel ou à l’enjeu immédiat si le fait le permet. '
        'Pas de réplique de la série, de slogan passe-partout ni de nouvel événement. '
        'Appelle get_match_context une fois avant de répondre. Utilise le score pour situer '
        'l’enjeu (égalité, avance ou retard) sans réciter les chiffres. '
        'Aucun chiffre, nom propre, geste, résultat ou détail de trajectoire dans ta réaction. '
        'Une phrase de 12 mots maximum, distincte de la réaction précédente. '
        f'Événement : {kind}. Réaction précédente : {previous or "aucune"}.'
    )
    reaction = agent.generate(prompt, schema, timeout=30, match_context=match_context).get('reaction')
    if not isinstance(reaction, str):
        raise ValueError('Réaction de Chester invalide.')
    reaction = reaction.strip()
    if (not re.fullmatch(r'[^.!?\n\r\d:<>]{8,90}[.!?]', reaction)
            or len(reaction.split()) > 12 or reaction.casefold() == (previous or '').casefold()):
        raise ValueError('Réaction de Chester invalide.')
    return {'reaction': reaction}
