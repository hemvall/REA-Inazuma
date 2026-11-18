"""One-click local delivery entry point."""
import os
from pathlib import Path
import webbrowser
import json
from urllib.request import Request,urlopen
from prepare_arena import ensure_built
from local_address import URL


def main():
    os.chdir(Path(__file__).resolve().parents[1])
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
