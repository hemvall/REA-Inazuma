"""Resolve special recruitment requests against the native player catalogue."""

from functools import lru_cache
import struct
import unicodedata

from club_fixtures import CLUB_TEAM_IDS
from nds import read_rom
from recruitment_rom import ROOT, encode_name


def validate_draft(draft):
    fields = {'name', 'short_name', 'level', 'template_unit'}
    if not isinstance(draft, dict) or set(draft) not in (fields, fields | {'team_id'}):
        raise ValueError('La fiche de recrutement est incomplète.')
    encode_name(draft['name'])
    encode_name(draft['short_name'])
    if type(draft['level']) is not int or not 1 <= draft['level'] <= 99:
        raise ValueError('Le niveau doit être compris entre 1 et 99.')
    if type(draft['template_unit']) is not int or not 0 < draft['template_unit'] < 0x8000:
        raise ValueError('Le poste doit correspondre à un modèle natif du Club.')
    team_id = draft.get('team_id', 1)
    if type(team_id) is not int or team_id not in CLUB_TEAM_IDS:
        raise ValueError('Équipe du Club inconnue.')
    return {**draft, 'team_id': team_id, 'name': draft['name'].strip(),
            'short_name': draft['short_name'].strip()}


@lru_cache(maxsize=1)
def native_players(rom_path):
    rom = read_rom(rom_path)
    units = rom.data[slice(*rom.files[ROOT + 'unitbase.dat'])]
    players = []
    for offset in range(0, len(units), 96):
        unit, = struct.unpack_from('<H', units, offset + 66)
        names = tuple(units[offset + field:offset + field + 32].split(b'\0', 1)[0].decode('latin1')
                      for field in (0, 32))
        if unit and all(names):
            players.append((unit, *names))
    return players


def normalize(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return ' '.join(''.join(char for char in text if not unicodedata.combining(char)).split())


def edit_distance(left, right):
    """Count edits, including a swap of two adjacent letters."""
    previous = list(range(len(right) + 1))
    before_previous = previous
    for i, char in enumerate(left, 1):
        current = [i]
        for j, other in enumerate(right, 1):
            cost = min(current[j-1] + 1, previous[j] + 1, previous[j-1] + (char != other))
            if i > 1 and j > 1 and char == right[j-2] and left[i-2] == other:
                cost = min(cost, before_previous[j-2] + 1)
            current.append(cost)
        before_previous, previous = previous, current
    return previous[-1]


def closest(target, rows):
    """Prefer exact full names, then exact aliases, then the closest spellings."""
    target = normalize(target)
    candidates = [(row, tuple(map(normalize, row[1:]))) for row in rows]
    exact = [row for row, names in candidates if target == names[0]]
    if exact:
        return exact
    exact = [row for row, names in candidates if target in names[1:]]
    if exact or len(target) < 3:
        return exact

    best = 1 if len(target) <= 5 else 2
    matches = []
    for row, names in candidates:
        distance = min((edit_distance(target, name) for name in names
                        if abs(len(target) - len(name)) <= best), default=best + 1)
        if distance < best:
            matches = []
            best = distance
        if distance == best:
            matches.append(row)
    return matches


def propose(rom_path, teams, party, message):
    words = message.strip().rstrip('.!?').split()
    # Keep the sentence structure and tolerate one typo in each opening verb.
    separators = [i for i in range(1, len(words) - 2)
                  if edit_distance(normalize(words[i]), 'peut') <= 1
                  and edit_distance(normalize(words[i+1]), 'recruter') <= 1]
    if len(separators) != 1:
        return 'Écris une demande comme « Raimon peut recruter Xene ».', None
    split, = separators
    team = ' '.join(words[:split])
    player = ' '.join(words[split+2:])
    team_matches = closest(team, [(row['id'], row['name']) for row in teams])
    if not team_matches:
        names = ', '.join(row['name'] for row in teams)
        return f'Équipe inconnue. Équipes disponibles : {names}.', None
    if len(team_matches) > 1:
        names = ', '.join(name for _, name in team_matches)
        return f'Quelle équipe voulais-tu dire : {names} ?', None

    team_id, team_name = team_matches[0]
    matches = closest(player, native_players(rom_path))
    if not matches:
        return f'Je ne trouve pas « {player} » dans le catalogue du jeu.', None
    if len(matches) > 1:
        names = ', '.join(dict.fromkeys(row[1] for row in matches[:8]))
        return f'Plusieurs joueurs correspondent à « {player} » : {names}. Précise le nom.', None

    unit, name, short_name = matches[0]
    roster = next(row['roster'] for row in teams if row['id'] == team_id)
    if unit in roster or (team_id == 1 and unit in party):
        return f'{name} fait déjà partie de {team_name}.', None
    try:
        draft = validate_draft({'name': name, 'short_name': short_name, 'level': 30,
                                'template_unit': unit, 'team_id': team_id})
    except ValueError:
        return f'Le nom de {name} ne peut pas être affiché dans une fiche de recrutement.', None
    return f'{team_name} peut recruter {name}.', draft
