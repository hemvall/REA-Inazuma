"""Regression check for the Windows console used by Lancer InazumIA.cmd."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from game_session import GameSession


def check_session(output):
    session = GameSession()
    try:
        opened = session.open('arena')
        sid = opened['session_id']
        observation = session.request(sid, 'observe')
        assert observation['match']['native_counter'] == 4, observation
        prepared = session.request(sid, 'prepare_match', revision=observation['revision'],
                                   home=10, away=3, lines=['Test console.'] * 6)
        assert 'error' not in prepared, prepared
        assert prepared['image'].startswith('iVBOR'), 'Missing PNG'
        Path(output).write_text(json.dumps({'ok': True}), encoding='utf-8')
    except Exception:
        Path(output).write_text(json.dumps({'error': traceback.format_exc()}), encoding='utf-8')
        raise
    finally:
        session.close()


if __name__ == '__main__':
    if len(sys.argv) == 2:
        check_session(sys.argv[1])
    elif sys.platform != 'win32':
        print('SKIP: Windows console required')
    else:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result.json'
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            # Do not redirect stdout/stderr: the child must use WindowsConsoleIO.
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(output)],
                                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                                    startupinfo=startup, timeout=150)
            report = json.loads(output.read_text(encoding='utf-8'))
            assert result.returncode == 0 and report.get('ok'), report
            print('PASS Windows console: arena boot, Zeus vs Occulte, PNG, close')
