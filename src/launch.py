"""One-click local delivery entry point."""
import os
from pathlib import Path
import threading
import webbrowser
import json
from urllib.request import Request,urlopen
from prepare_arena import ensure_built


def main():
    os.chdir(Path(__file__).resolve().parents[1])
    try:
        request=Request('http://127.0.0.1:8765/api/capabilities',data=b'{}',headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=2) as response:
            existing=json.load(response)
        if existing.get('application')=='InazumIA':
            webbrowser.open('http://127.0.0.1:8765')
            return
    except (OSError,ValueError):
        pass
    ensure_built()
    from web_server import main as serve
    opener=threading.Timer(1,lambda:webbrowser.open('http://127.0.0.1:8765'))
    opener.daemon=True
    opener.start()
    serve()


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError) as error:
        print('InazumIA : '+str(error))
        raise SystemExit(1)
