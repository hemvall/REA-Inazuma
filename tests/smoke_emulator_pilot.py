"""Exercise the semantic pilot against isolated native emulator sessions."""
import base64
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena_service import Arena


def reject(operation, expected):
    try:
        operation()
    except ValueError as error:
        assert expected in str(error), error
    else:
        raise AssertionError(f'Expected rejection: {expected}')


def main():
    arena = Arena()
    try:
        lines = ['Le match commence.'] * 6
        evidence = Path('build/pilot-smoke')
        evidence.mkdir(parents=True, exist_ok=True)
        for home, away in [(3, 10), (10, 3)]:
            arena.prepare(home, away, lines)
            sid = arena.session.session_id
            args = {'session_id': sid}
            state = arena.call('observe_match', args)
            checkpoint = arena.call('checkpoint_save', args)
            command = {**args, 'revision': state['revision'], 'frame': state['frame']}
            apply = lambda **values: arena.call('apply_match_action', {**command, **values})
            reject(lambda: apply(action_id='shot.goal'), 'Action indisponible')
            reject(lambda: apply(action_id='match.start', revision=state['revision'] - 1), 'Observation périmée')
            reject(lambda: apply(action_id='match.start', frame=state['frame'] - 1), 'Observation périmée')
            reject(lambda: apply(action_id='match.start', actor='agent'), 'Contrôle détenu par human')
            reject(lambda: arena.call('advance_match', {**args, 'revision': state['revision'], 'frames': 121}),
                   'Expected 1..120 frames')
            assert arena.call('observe_match', args) == state
            started = apply(action_id='match.start')
            assert started['frame'] > state['frame']
            arena.call('checkpoint_load', {**args, 'revision': started['revision'],
                                          'checkpoint_id': checkpoint['checkpoint_id']})
            arena.delegate(sid, max_decisions=500)
            arena.thread.join(180)
            assert not arena.thread.is_alive(), 'Pilot timeout'
            report = arena.status()
            assert report['owner'] == 'human'
            assert report['job']['text_calls'] == report['job']['vision_calls'] == 0
            assert arena.session.video_frame()[1], 'No live video frame'
            snapshot = arena.call('observe', args)
            (evidence / f'{home}-{away}.png').write_bytes(base64.b64decode(snapshot['image']))
            if report['job']['state'] == 'blocked':
                saved = arena.call('checkpoint_save', args)
                for method in ('idle', 'A', 'touch'):
                    if method != 'idle':
                        arena.call('checkpoint_load', {**args, 'revision': snapshot['revision'],
                                                      'checkpoint_id': saved['checkpoint_id']})
                        snapshot = arena.call('observe', args)
                    snapshot = arena.call('step', {
                        **args, 'revision': snapshot['revision'], 'frames': 10 if method == 'idle' else 6,
                        'keys': ['A'] if method == 'A' else [],
                        'touch': [128, 96] if method == 'touch' else None,
                    })
                    snapshot = arena.call('step', {**args, 'revision': snapshot['revision'],
                                                   'keys': [], 'frames': 120})
                    (evidence / f'{home}-{away}-{method}.png').write_bytes(base64.b64decode(snapshot['image']))
            print(json.dumps({'home': home, 'away': away, 'job': report['job'],
                              'screen': report['observation']['match']['screen']['name']},
                             ensure_ascii=True), flush=True)
            arena.session.close()
            arena.fixture = None
            arena.latest = None
        arena.prepare(3, 10, lines)
        sid = arena.session.session_id
        arena.delegate(sid)
        deadline = time.monotonic() + 5
        while arena.session.owner != 'agent' and time.monotonic() < deadline:
            time.sleep(.01)
        assert arena.session.owner == 'agent', 'Pilot never acquired control'
        arena.call('stop_agent', {'session_id': sid})
        arena.thread.join(15)
        assert not arena.thread.is_alive() and arena.session.owner == 'human'
        state = arena.call('observe_match', {'session_id': sid})
        reject(lambda: arena.call('advance_match', {'session_id': sid, 'actor': 'agent',
                                                     'revision': state['revision'], 'frames': 1}),
               'Contrôle détenu par human')
        print('PASS: handoff revoked pilot commands', flush=True)
    finally:
        arena.stop()
        if arena.thread:
            arena.thread.join(15)
        arena.session.close()


if __name__ == '__main__':
    main()
