"""Run isolated matches repeatedly and retain the evidence for each handoff."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arena_service import Arena


def play(home, away, timeout, folder, mode='deterministic'):
    arena = Arena(stream_video=False)
    try:
        arena.prepare(home, away, ['Le match commence.'] * 6)
        sid = arena.session.session_id
        arena.delegate(sid, max_decisions=500, mode=mode)
        arena.thread.join(timeout)
        timed_out = arena.thread.is_alive()
        if timed_out:
            arena.stop(sid)
            arena.thread.join(20)
            if arena.thread.is_alive():
                raise RuntimeError('Le pilote ne s’est pas arrêté après son délai.')
        status = arena.status()
        state = arena.call('observe', {'session_id': sid})
        prefix = folder / status['job']['id']
        prefix.with_suffix('.png').write_bytes(base64.b64decode(state.pop('image')))
        compact = arena.call('observe_match', {'session_id': sid})
        report = {'home': home, 'away': away, 'session_id': sid, 'timeout': timed_out,
                  'job': status['job'], 'owner': status['owner'],
                  'match': compact, 'last_actions': arena.history[-8:],
                  'journal': str(Path('build/agents') / f"{status['job']['id']}-match.jsonl"),
                  'screenshot': str(prefix.with_suffix('.png'))}
        prefix.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        return report
    finally:
        arena.stop()
        if arena.thread:
            arena.thread.join(20)
        arena.session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=2, help='Number of runs per fixture')
    parser.add_argument('--timeout', type=int, default=240, help='Seconds per match')
    parser.add_argument('--home', type=int, choices=(3, 10), help='Run only the selected home team')
    parser.add_argument('--mode', choices=('deterministic', 'ai'), default='deterministic')
    args = parser.parse_args()
    if args.rounds < 1 or args.timeout < 1:
        parser.error('rounds and timeout must be positive')
    folder = Path('build/pilot-replays') / str(time.time_ns())
    folder.mkdir(parents=True)
    print(str(folder), flush=True)
    fixtures = [(home, away) for home, away in ((3, 10), (10, 3))
                if args.home is None or home == args.home]
    for _ in range(args.rounds):
        for home, away in fixtures:
            try:
                print(json.dumps(play(home, away, args.timeout, folder, args.mode)), flush=True)
            except (ValueError, RuntimeError, OSError) as error:
                print(json.dumps({'home': home, 'away': away, 'error': str(error)}), flush=True)


if __name__ == '__main__':
    main()
