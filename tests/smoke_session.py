"""Explicit integration check against the local ROM/core, not unittest discovery."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from game_session import GameSession


if __name__ == '__main__':
    session = GameSession()
    try:
        identity = session.open()
        sid = identity['session_id']
        result = session.request(sid, 'step', revision=0, frames=120, keys=[])
        assert result['frame'] == 120 and result['revision'] == 1, result
        assert result['image'].startswith('iVBOR'), 'Missing PNG'
        stale = session.request(sid, 'step', revision=0, frames=1, keys=['A'])
        assert stale['error'] == 'Stale revision', stale
        result = session.request(sid, 'observe')
        assert result['frame'] == 120, result
        checkpoint = session.request(sid, 'checkpoint_save')['checkpoint_id']
        session.request(sid, 'step', revision=1, frames=5, keys=[])
        restored = session.request(sid, 'checkpoint_load', revision=2, checkpoint_id=checkpoint)
        assert restored['frame'] == 120 and restored['revision'] == 3, restored
        session.set_control(sid, 'agent')
        try:
            session.request(sid, 'step', revision=3, frames=1, keys=[])
            raise AssertionError('Human command accepted during agent control')
        except ValueError:
            pass
        session.set_control(sid, 'human')
        print('PASS boot, 120 frames, PNG, stale revision, non-mutating observe', identity)
    finally:
        session.close()
