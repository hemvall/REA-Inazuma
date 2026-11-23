"""Native regression: the reverse fixture must load both exact 16-player rosters."""
import base64
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from game_session import GameSession


if __name__=='__main__':
    session=GameSession()
    try:
        identity=session.open('arena');sid=identity['session_id']
        state=session.request(sid,'prepare_match',revision=0,home=10,away=3,lines=[
            'Zeus accueille Occulte.','Occulte releve le defi.',
            'Notre equipe est prete.','Chaque passe va compter.',
            'Jouons notre meilleur football.','Que le meilleur gagne !'])
        assert 'error' not in state,state
        state=session.request(sid,'start_match',revision=state['revision'])
        for index in range(50):
            state=session.request(sid,'step',revision=state['revision'],frames=3,keys=['A'])
            if index%3==2:
                state=session.request(sid,'step',revision=state['revision'],frames=3,touch=[128,96])
            for _ in range(4):
                state=session.request(sid,'step',revision=state['revision'],frames=120,keys=[])
            match=state['match']
            print(index,match['phase'],len(match['home_units']),len(match['away_units']),flush=True)
            if match['away_units']:
                assert set(match['home_units'])==set(range(181,197)),match
                assert set(match['away_units'])==set(range(41,57)),match
                folder=Path('build/delivery');folder.mkdir(exist_ok=True)
                (folder/'reverse-rosters.png').write_bytes(base64.b64decode(state.pop('image')))
                (folder/'reverse-rosters.json').write_text(json.dumps({'identity':identity,'state':state},indent=2))
                print('PASS Zeus home and Occulte away: both complete native rosters',flush=True)
                break
        else:raise AssertionError('Reverse native rosters were not reached')
    finally:session.close()
