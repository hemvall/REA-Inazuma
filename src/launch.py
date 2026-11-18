"""One-click local delivery entry point."""
import os
from pathlib import Path
import shutil
import subprocess
import webbrowser
import json
from urllib.request import Request,urlopen
from prepare_arena import ensure_built
from local_address import URL


def start_lm_studio():
    # An explicitly configured endpoint is managed outside the launcher.
    if os.environ.get('INAZUMIA_LLM_URL', 'http://127.0.0.1:1234/v1').rstrip('/') != 'http://127.0.0.1:1234/v1':
        return

    bundled_cli = Path.home()/'.lmstudio/bin/lms.exe'
    cli = str(bundled_cli) if bundled_cli.is_file() else shutil.which('lms')
    if not cli:
        print('Coach local : commande lms introuvable. Démarrez le serveur LM Studio manuellement.')
        return

    model = os.environ.get('INAZUMIA_LLM_MODEL', 'qwen/qwen3.5-9b')
    try:
        subprocess.run([cli, 'server', 'start', '--port', '1234', '--bind', '127.0.0.1'],
                       check=True, timeout=30)
        running = subprocess.run([cli, 'ps', '--json'], check=True, timeout=15,
                                 capture_output=True, encoding='utf-8')
        if not any(entry.get('identifier') == model for entry in json.loads(running.stdout)):
            print(f'Coach local : chargement de {model} dans LM Studio.', flush=True)
            subprocess.run([cli, 'load', model, '--identifier', model, '--yes'],
                           check=True, timeout=180)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Coach local : préparation de LM Studio incomplète. {error}', flush=True)


def main():
    os.chdir(Path(__file__).resolve().parents[1])
    start_lm_studio()
    try:
        request=Request(URL+'/api/capabilities',data=b'{}',headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=2) as response:
            existing=json.load(response)
        if existing.get('application')=='InazumIA':
            webbrowser.open(URL)
            return
    except (OSError,ValueError):
        pass
    ensure_built()
    from web_server import main as serve
    serve(on_ready=lambda:webbrowser.open(URL))


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError) as error:
        print('InazumIA : '+str(error))
        raise SystemExit(1)
