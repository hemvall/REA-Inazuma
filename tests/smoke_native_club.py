"""ROM-only acceptance: fresh boot, both route choices and actual native squads.

No bridge, memory writes, browser or externally modified savestate is used.
"""
import ctypes as C
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from prepare_arena import ensure_built
from emulator_probe import Emulator
from arena_bridge import catalogue
from scene_team import inspect_party_memory


def main():
    ensure_built('club_native')
    folder=Path('build/club_native/acceptance');folder.mkdir(parents=True,exist_ok=True)
    e=Emulator('build/club_native/arena.nds','local/tools/melonds-core/melonds_libretro.dll',str(folder/'system'))
    def ram():return C.string_at(e.lib.retro_get_memory_data(2),4*1024*1024)
    def step(frames=120,keys=(),touch=None,name=None):
        command={'frames':frames,'keys':list(keys)}
        if touch is not None:command['touch']=touch
        if name:command['capture']=str(folder/(name+'.png'))
        e.command(command)
    def press():step(2,['A']);step()
    teams={t['id']:t for t in catalogue()}
    results=[]
    try:
        state=folder/'route.state'
        if '--resume' not in sys.argv:
            for command in json.loads(Path('profiles/arena_boot.json').read_text()):
                e.command(command)
                if struct.unpack_from('<I',ram(),0xDBEBC+20)[0]==10500:break
            else:raise AssertionError('Native club did not boot')
            step(600);step(28,['UP']);step(4);press()
            for _ in range(8):press()
            step(name='route')
            e.command({'save':str(state)})
        for label,x,home,away in (('occulte-zeus',84,3,10),('royal-raimon',196,2,1)):
            e.command({'load':str(state)})
            step(20,touch=[x,68]);step(name=label+'-selected')
            for _ in range(16):
                press()
                if struct.unpack_from('<I',ram(),0xDBEBC+32)[0]==10:break
            step(600)
            m=ram();party=inspect_party_memory(m)
            owned={p['unit'] for p in party if not p['team_field']&0x8000}
            opponents={p['unit'] for p in party if p['team_field']&0x8000}
            assert owned==set(teams[home]['roster'])-{0},(label,'home',owned)
            assert opponents==set(teams[away]['roster'])-{0},(label,'away',opponents)
            names=[m[a:a+32].split(b'\0')[0].decode('cp1252') for a in (0xE889C,0xE88DC)]
            assert names==[teams[home]['name'],teams[away]['name']],names
            step(name=label+'-launch')
            results.append({'fixture':label,'names':names,'home':sorted(owned),'away':sorted(opponents)})
        # B exits the native board and restores the isolated exploration party.
        e.command({'load':str(state)})
        step(20,['B']);step()
        press()  # Confirm the native "Voulez-vous quitter ?" prompt.
        step(600)
        owned={p['unit'] for p in inspect_party_memory(ram()) if not p['team_field']&0x8000}
        assert owned=={1,3,29,190,2430},owned
        step(name='cancelled')
        (folder/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print('Native route: both fixtures launched with correct teams; cancel restored party.',flush=True)
    except Exception:
        import traceback
        (folder/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        e.command({'memory':str(folder/'failed.ram'),'capture':str(folder/'failed.png')})
        raise
    finally:e.lib.retro_unload_game();e.lib.retro_deinit()


if __name__=='__main__':main()
