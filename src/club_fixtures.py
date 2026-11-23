"""Native clubhouse offers. Team IDs refer to the original team catalogue."""
FIXTURES = {
    1: (3, 10, 'Occulte contre Zeus'),
    2: (2, 1, 'Royal Academy contre Raimon'),
    3: (10, 3, 'Zeus contre Occulte'),
    4: (1, 2, 'Raimon contre Royal Academy'),
    5: (41, 33, 'Empereurs noirs\\ncontre Genesis'),
    6: (33, 41, 'Genesis contre\\nEmpereurs noirs'),
}
CLUB_FIXTURE = max(FIXTURES) + 1
CLUB_TEAM_IDS = frozenset(team for home, away, _ in FIXTURES.values() for team in (home, away))


def dialogue(home, away):
    return [
        'Un match amical ? Nous sommes prets !',
        'Alors jouons avec nos propres equipes.',
        'Que chacun donne le meilleur de lui-meme.',
        'Nous ne vous ferons aucun cadeau !',
        'Peu importe le resultat, faisons un beau match.',
        'Rendez-vous sur le terrain !',
    ]
