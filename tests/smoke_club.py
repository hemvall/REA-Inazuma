"""Real melonDS acceptance: native NPC, four fixtures, cancel and roster restore.

Run explicitly with the user's local ROM/core; artifacts remain ignored.
"""
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from game_session import GameSession
from arena_bridge import catalogue


def main():
    game=GameSession()
    folder=Path('build/club/acceptance');folder.mkdir(parents=True,exist_ok=True)
    try:
        identity=game.open('club');sid=identity['session_id']
        value=game.request(sid,'observe')
        initial_party=value['match']['party_units']
        evidence=[]

        def step(keys=(),frames=120,touch=None):
            nonlocal value
            value=game.request(sid,'step',revision=value['revision'],frames=frames,keys=list(keys),touch=touch)
            if 'error' in value: raise RuntimeError(value)
            return value['match']

        def press(key='A'):
            step([key],2);return step()

        def capture(name):
            (folder/(name+'.png')).write_bytes(base64.b64decode(value['image']))
            record={k:v for k,v in value.items() if k!='image'}
            evidence.append({'name':name,**record})
            print(name,record['match']['phase'],flush=True)

        step(['UP'],28)
        capture('room')
        world=game.request(sid,'checkpoint_save')['checkpoint_id']

        def talk():
            press();press();press()
            assert value['match']['phase']=='choosing',value['match']

        def restore_world():
            nonlocal value
            value=game.request(sid,'checkpoint_load',revision=value['revision'],checkpoint_id=world)
            assert value['match']['phase']=='club',value

        teams={row['id']:row for row in catalogue()}
        for home,away,skip in ((3,10,0),(2,1,1),(10,3,2),(1,2,3)):
            restore_world();talk()
            for _ in range(skip):
                step(['DOWN'],2);press()
            capture(f'offer-{home}-{away}')
            for _ in range(5):
                if value['match']['fixture']:break
                press()
            assert (value['match']['fixture']['home'],value['match']['fixture']['away'])==(home,away),value['match']
            capture(f'prepared-{home}-{away}')
            for _ in range(50):
                match=value['match']
                if match['away_units']:break
                if match['native_counter']==10:
                    step(frames=2,touch=[128,90]);step();press()
                else:press()
            match=value['match']
            assert set(match['home_units'])==set(teams[home]['roster'])-{0},match
            assert set(match['away_units'])==set(teams[away]['roster'])-{0},match
            capture(f'match-{home}-{away}')
            # Let the native match introduction settle, then dismiss its stylus
            # prompt and reach the original formation screen before returning.
            for _ in range(5):step()
            for _ in range(3):
                step(frames=2,touch=[128,90]);step();press()
            capture(f'formation-{home}-{away}')
            step(frames=2,touch=[225,174]);step()
            for _ in range(5):step()
            for _ in range(3):
                step(frames=2,touch=[225,174]);step()
            capture(f'field-{home}-{away}')
            value=game.request(sid,'reset_match',revision=value['revision'])
            assert value['match']['phase']=='club' and value['match']['fixture'] is None,value
            assert value['match']['party_units']==initial_party,value['match']
            capture(f'returned-{home}-{away}')
            assert game.open('club')['rom_sha256']==identity['rom_sha256']

        restore_world();talk()
        for _ in range(4):
            step(['DOWN'],2);press()
        for _ in range(5):
            if value['match']['phase']=='club':break
            press()
        assert value['match']['phase']=='club' and value['match']['fixture'] is None,value['match']
        assert value['match']['party_units']==initial_party,value['match']
        capture('cancelled')
        (folder/'verification.json').write_text(json.dumps({'identity':identity,'initial_party':initial_party,'steps':evidence},indent=2),encoding='utf-8')
        print('PASS native NPC choices, four fixtures, same ROM/session, restore and cancellation',flush=True)
    finally:
        game.close()


if __name__=='__main__':main()
