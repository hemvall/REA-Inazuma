"""Exercise compact observations and hybrid routing in an isolated native worker.

No model API and no existing web session are used. Stop at the first unfamiliar
screen rather than guessing a gameplay input.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from arena_service import Arena


class StopAtInference:
    backend = 'test'
    model = 'no model API'

    def __init__(self):
        self.calls = []

    def play(self, image, state, history, cancel):
        self.calls.append({'mode':'text' if image is None else 'vision','state':state})
        return {'intent':'blocked','reason':'Arrêt de vérification au premier appel modèle.',
                'frames':1,'keys':[],'touch':None,'path':[]}


def main():
    arena = Arena()
    arena.agent = StopAtInference()
    try:
        arena.prepare(3,10,['Vérification locale.']*6)
        sid = arena.session.session_id
        compact = arena.checked('observe',session_id=sid,include_image=False)
        assert 'image' not in compact
        assert 'screen' in compact['match']
        assert 'tactical' in compact['match']
        arena.delegate(sid,max_decisions=40)
        arena.thread.join(120)
        assert not arena.thread.is_alive(), 'Hybrid smoke timed out'
        assert arena.job['state'] == 'complete', arena.job
        assert arena.session.owner == 'human'
        assert arena.agent.calls, 'Expected to reach a model fallback'
        report = {'job':arena.job,'calls':arena.agent.calls,'history':arena.history,
                  'observation':{key:value for key,value in arena.latest.items() if key!='image'}}
        folder = Path('build/hybrid-player')
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'session-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'job':arena.job,'model_calls':len(arena.agent.calls)},ensure_ascii=False))
    finally:
        arena.stop()
        if arena.thread:arena.thread.join(5)
        arena.session.close()


if __name__ == '__main__':
    main()
