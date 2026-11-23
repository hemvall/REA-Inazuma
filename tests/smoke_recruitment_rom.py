"""Exercise the web Club recruitment service against the actual melonDS core."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from arena_bridge import catalogue
from arena_service import Arena
from recruitment import closest, validate_draft
from nds import sha
from recruitment_rom import FIRST_RECRUIT_ID
from scene_team import ROSTER


def main():
    arena = Arena(stream_video=False, recruit_in_club=True)
    with TemporaryDirectory(dir=ROOT / 'build') as directory:
        arena.session.recruitment_save = Path(directory) / 'club.save'
        try:
            (exercise_lobby if '--lobby' in sys.argv else exercise)(arena)
        finally:
            arena.session.close()


def exercise(arena):
    open_club = lambda: arena.session.open('club')['session_id']
    sid = open_club()

    def observe():
        return arena.checked('observe', session_id=sid, include_image=False)

    def revise(message):
        arena.call('recruitment_turn', {'session_id': sid, 'message': message})
        arena.thread.join(5)
        assert arena.job['state'] == 'complete', arena.job
        return arena.status()['recruitment']

    def step(keys=(), frames=120, touch=None):
        revision = arena.latest['revision']
        return arena.checked('step', session_id=sid, revision=revision, include_image=False,
                             frames=frames, keys=list(keys), touch=touch)

    def press(key='A'):
        step((key,), 2)
        return step()

    assert observe()['match']['party_units'] == list(ROSTER)
    cancelled = revise('raimon peut recruter xene')
    arena.call('recruitment_cancel', {'session_id': sid})
    assert arena.status()['recruitment'] is None
    assert observe()['match']['party_units'] == list(ROSTER)

    first = revise('raimon peut recruter xene')
    for team_id, name in [(1, 'Raimon'), (2, 'Royal Acadmy'), (3, 'Oculte'), (10, 'Zues')]:
        sheet = revise(f'{name} peut recruter Xnee')['draft']
        assert sheet['team_id'] == team_id and sheet['template_unit'] == 2151
    already_owned = revise('Occulte peut recruter Talisman')
    assert already_owned['draft'] is None
    assert closest('Xeae', [(1, 'Xene'), (2, 'Xeze')]) == [(1, 'Xene'), (2, 'Xeze')]
    assert validate_draft({'name': 'Xene', 'short_name': 'Xene',
                           'level': 30, 'template_unit': 2151})['team_id'] == 1
    unknown = revise('Raimon peut recruter Joueur Inconnu')
    assert unknown['draft'] is None
    updated = revise('Zues peutt recrtuer Xnee !')
    assert updated['draft'] == {'name': 'Xene', 'short_name': 'Xene', 'level': 30,
                                'template_unit': 2151, 'team_id': 10}
    assert len({cancelled['version'], first['version'], updated['version']}) == 3

    def confirm(version=updated['version'], revision=None):
        return arena.call('recruitment_confirm', {'session_id': sid, 'version': version,
                          'revision': arena.latest['revision'] if revision is None else revision})

    for invalid in (lambda: confirm(first['version']), lambda: confirm(revision=-1)):
        try:
            invalid()
        except ValueError as error:
            assert 'périm' in str(error), error
        else:
            raise AssertionError('Une confirmation obsolète a réussi.')
    try:
        confirm()
    except ValueError as error:
        assert 'devant le coach' in str(error), error
    else:
        raise AssertionError('Le recrutement a réussi hors de portée du coach.')
    assert observe()['match']['party_units'] == list(ROSTER)
    assert arena.status()['recruitment']['version'] == updated['version']
    assert not arena.session.recruitment_save.exists()
    step(('UP',), 28)
    enrolled = confirm()
    assert confirm() == enrolled
    assert enrolled['unit'] == FIRST_RECRUIT_ID
    assert enrolled['observation']['match']['party_units'] == [*ROSTER, FIRST_RECRUIT_ID]
    native = {'unit': FIRST_RECRUIT_ID, 'name': 'Xene', 'short_name': 'Xene', 'level': 30, 'team_id': 10}
    assert enrolled['observation']['native_recruit'] == native
    rom = ROOT / 'build/sessions' / sid / 'recruited.nds'
    print(f'Inscription native, ROM BEBF rev 0 {sha(rom.read_bytes())}', flush=True)

    press()
    press()
    match = press()['match']
    assert match['phase'] == 'choosing', match
    for _ in range(4):
        step(('DOWN',), 2)
        match = press()['match']
    for _ in range(5):
        if match['fixture']:
            break
        match = press()['match']
    assert match['fixture']['club_squad'], match
    assert (match['fixture']['home'], match['fixture']['away']) == (10, 1), match
    for _ in range(50):
        if match['away_units']:
            break
        if match['native_counter'] == 10:
            step(frames=2, touch=[128, 90])
            step()
        match = press()['match']
    zeus = next(team for team in catalogue() if team['id'] == 10)
    starters = [unit for unit in zeus['roster'] if unit][:10] + [FIRST_RECRUIT_ID]
    assert match['home_units'][:11] == starters, match
    print(f'Effectif natif du match {match["home_units"]}', flush=True)
    for _ in range(5):
        step()
    for x, y in [(128, 90)] * 3 + [(225, 174)] * 4 + [(70, 174)] * 4:
        step(frames=2, touch=[x, y])
        match = step()['match']
        if any(row['unit'] == FIRST_RECRUIT_ID for row in match['tactical']['positions']):
            break
    assert any(row['unit'] == FIRST_RECRUIT_ID for row in match['tactical']['positions']), match
    print(f'Recrue alignée sur le terrain, identifiant {FIRST_RECRUIT_ID}', flush=True)
    returned = arena.checked('reset_match', session_id=sid, revision=arena.latest['revision'],
                             include_image=False)
    assert returned['match']['party_units'] == [*ROSTER, FIRST_RECRUIT_ID]
    arena.session.close()
    sid = open_club()
    resumed = observe()
    assert resumed['match']['party_units'] == [*ROSTER, FIRST_RECRUIT_ID]
    assert resumed['recruited'] == updated['draft']
    assert resumed['native_recruit'] == native
    print(f'Reprise native {resumed["recruited"]}', flush=True)

    extra = revise('Zeus peut recruter Mark Evans')
    appended = confirm(extra['version'])
    assert appended['unit'] == FIRST_RECRUIT_ID + 1
    arena.session.close()
    sid = open_club()
    assert observe()['native_recruit'] == native
    assert len(arena.status()['recruited_players']) == 2
    print('Deuxième recrutement conservé après reprise du Club', flush=True)


def exercise_lobby(arena):
    assert arena.status()['session_id'] is None
    arena.call('recruitment_turn', {'session_id': None, 'message': 'Zues peut recruter Xnee'})
    arena.thread.join(5)
    assert arena.job['state'] == 'complete', arena.job
    sheet = arena.status()['recruitment']
    result = arena.call('recruitment_confirm', {'session_id': None, 'version': sheet['version']})
    assert result['draft']['team_id'] == 10
    first = result['draft']
    assert arena.status()['recruited_players'] == [first]
    arena.call('recruitment_turn', {'session_id': None, 'message': 'Zeus peut recruter Mark Evans'})
    arena.thread.join(5)
    assert arena.job['state'] == 'complete', arena.job
    sheet = arena.status()['recruitment']
    second = arena.call('recruitment_confirm', {'session_id': None, 'version': sheet['version']})
    assert second['unit'] == FIRST_RECRUIT_ID + 1
    assert arena.status()['recruited_players'] == [first, second['draft']]
    print('Recrutement confirmé depuis le salon', flush=True)

    for home, away, side in ((10, 1, 'home_units'), (1, 10, 'away_units')):
        result = arena.prepare(home, away, ['Place au match !'] * 6)
        sid = arena.session.session_id

        def command(op, **args):
            return arena.checked(op, session_id=sid, revision=arena.latest['revision'],
                                 include_image=False, **args)

        match = command('start_match')['match']
        for _ in range(30):
            if match['away_units']:
                break
            if match['native_counter'] == 10:
                command('step', keys=[], frames=2, touch=[128, 90])
                command('step', keys=[], frames=120)
            else:
                command('step', keys=['A'], frames=2)
            match = command('step', keys=[], frames=120)['match']
        assert {FIRST_RECRUIT_ID, FIRST_RECRUIT_ID + 1} <= set(match[side]), match
        print(f'Arène, recrue présente dans {side}', flush=True)
        command('reset_match')
    arena.session.close()

    sid = arena.session.open('club')['session_id']
    local = arena.checked('observe', session_id=sid, include_image=False)
    assert local['native_recruit']['unit'] == FIRST_RECRUIT_ID
    assert local['native_recruit']['team_id'] == 10
    assert FIRST_RECRUIT_ID in local['match']['party_units']
    print('Recrue importée dans le local', flush=True)


if __name__ == '__main__':
    main()
