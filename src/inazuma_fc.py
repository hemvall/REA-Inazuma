"""Map the club's stable browser IDs to the French arena player database."""
from recruitment import native_players
from recruitment_rom import FIRST_RECRUIT_ID

TEAM_ID = 1000
TEAM_NAME = 'Inazuma FC'
STARTERS = 11
SQUAD_SIZE = 16
SCOUTS = (529, 530, 519, 523, 534, 536, 520, 525, 526, 527, 528, 524, 532, 540, 531, 533)
UNITS = {
    **{f'scout-{i}': unit for i, unit in enumerate(SCOUTS, 1)},
    'willy': 12, 'steve': 6, 'tod': 5, 'max': 9, 'darren': 2381, 'jim': 4,
    'tim': 7, 'sam-kincaid': 8, 'peter-drent': 22, 'nathan-jones': 41,
    'chuck-dollman': 53, 'erik': 1091, 'kevin': 11, 'jack': 3,
    'celia': 14, 'bobby': 1092, 'daniel-hatch': 29, 'rob-crombie': 52,
    'bruce-monkey': 68, 'neil-turner': 91, 'mark': 1, 'axel': 10, 'joseph-king': 21,
    'david-samford': 31, 'hurley': 2404, 'caleb': 2370, 'shawn': 2329,
    'nathan': 2430, 'xene': 2151, 'jude': 30,
    'byron': 190, 'torch': 2090, 'gazelle': 2089,
}
# Missing characters and story-only entries use named copies of playable units.
VARIANTS = {
    'hekyll': (42, 'Hekyll Jyde', 'Jyde'),
    'archer': (2404, 'Archer Hawkins', 'Archer'),
    'austin': (11, 'Austin Hobbes', 'Austin'),
    'xavier-foster': (2151, 'Xavier Foster', 'Xavier'),
    'xavier-schiller': (2151, 'Xavier Schiller', 'Xavier'),
    'aiden-child': (2337, 'Aiden Froste (enfant)', 'Aiden enfant'),
    'aiden-adult': (2329, 'Aiden Froste (adulte)', 'Aiden adulte'),
}
# The game's team table lists the keeper first, followed by defence, midfield and attack.
NATIVE_ORDER = (10, 6, 7, 8, 9, 2, 3, 4, 5, 0, 1, 11, 12, 13, 14, 15)


def prepare_squad(lineup, rom_path, first_clone, opposing_units):
    if not isinstance(lineup, list) or len(lineup) != SQUAD_SIZE:
        raise ValueError('Composition Inazuma FC invalide.')
    if any(player is None for player in lineup[:STARTERS]):
        raise ValueError('Complète les onze postes titulaires d’Inazuma FC avant le match.')
    selected = [lineup[index] for index in NATIVE_ORDER if lineup[index] is not None]
    if (any(not isinstance(player, str) or player not in UNITS and player not in VARIANTS
            for player in selected) or len(set(selected)) != len(selected)):
        raise ValueError('La composition d’Inazuma FC contient un joueur inconnu ou en double.')
    names = {unit: (name, short_name) for unit, name, short_name in native_players(rom_path)}
    squad, drafts = [], []
    for player in selected:
        if player in VARIANTS:
            template, name, short_name = VARIANTS[player]
        else:
            template = UNITS[player]
            name, short_name = names[template]
        unit = template
        # The native match suppresses a shared unit ID on the away side.
        if player in VARIANTS or template in opposing_units:
            unit = FIRST_RECRUIT_ID + first_clone + len(drafts)
            drafts.append({'template_unit': template, 'name': name, 'short_name': short_name})
        squad.append((unit, name))
    return squad, drafts
