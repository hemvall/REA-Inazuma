"""Run a real arena match with LM Studio; require a native final screen."""
import base64
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena_service import Arena


def main():
    arena = Arena()
    folder = Path('build/lm-match')
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        arena.select_agent('local')
        arena.prepare(3, 10, ['Occulte est pret.', 'Zeus releve le defi.',
                             'Le terrain nous attend.', 'Que le meilleur gagne.',
                             'Nous jouerons ensemble.', 'En place pour le match.'])
        sid = arena.session.session_id
        # Measure the same two-frame requests used by the web player.
        timings = []
        for _ in range(30):
            before = time.monotonic()
            arena.checked('step', session_id=sid, revision=arena.latest['revision'], frames=2, keys=[])
            timings.append(time.monotonic() - before)
        print(json.dumps({'two_frame_request_ms': sum(timings)*1000/len(timings)}), flush=True)
        arena.delegate(sid, max_decisions=500)
        last = ''
        deadline = time.monotonic() + 7200
        while arena.thread.is_alive():
            arena.thread.join(1)
            state = arena.status()
            text = state['job']['message']
            if text != last:
                print(text, flush=True)
                last = text
            if time.monotonic() > deadline:
                arena.stop()
                raise TimeoutError('Full-match test exceeded two hours')
        state = arena.status()
        observation = arena.checked('observe', session_id=sid)
        (folder/'final.png').write_bytes(base64.b64decode(observation.pop('image')))
        report = {'job': state['job'], 'observation': observation, 'actions': arena.history,
                  'elapsed_seconds': time.monotonic()-started,
                  'two_frame_request_ms': sum(timings)*1000/len(timings),
                  'backend': arena.agent.backend, 'model': arena.agent.model}
        (folder/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        assert state['job']['state'] == 'complete', state['job']
        assert state['owner'] == 'human', 'Control not returned'
        assert arena.history, 'No player action executed'
        assert not state['job']['vision_calls'] and not state['job']['text_calls'], state['job']
        assert observation['match']['phase'] == 'result', 'Native final result not reached'
        assert observation['match']['result_source'] == 'native_final_screen'
        print('PASS: local player reached the native final match screen without model calls', flush=True)
    finally:
        arena.stop()
        if arena.thread:
            arena.thread.join(5)
        arena.session.close()


if __name__ == '__main__':
    main()
