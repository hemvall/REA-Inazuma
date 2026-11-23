"""Loopback-only web service. Run python src/web_server.py."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time
import threading
from pathlib import Path
from arena_service import Arena
from chester import generate_reaction
from local_address import HOST, PORT, URL

ARENA = Arena(local_only=True, recruit_in_club=True)
WEB = Path(__file__).resolve().parents[1] / 'web'
CHESTER_MODEL = threading.Lock()


def chester_reaction(session_id, epoch, event_id, previous=None, mode='chester'):
    if mode not in ('chester', 'neuille'):
        raise ValueError('Mode de commentaire inconnu.')
    if previous is not None and (not isinstance(previous, str) or len(previous) > 91):
        raise ValueError('Réaction précédente invalide.')
    commentary = (ARENA.latest or {}).get('commentary', {})
    if (session_id != ARENA.session.session_id or session_id != commentary.get('session_id')
            or epoch != commentary.get('epoch')):
        return {}
    event = next((item for item in commentary.get('events', ()) if item['id'] == event_id), None)
    if not event or time.time() - event['at'] > 4 or not CHESTER_MODEL.acquire(blocking=False):
        return {}
    context = None

    def read_match_context():
        nonlocal context
        current = (ARENA.latest or {}).get('commentary', {})
        if (session_id != ARENA.session.session_id or session_id != current.get('session_id')
                or epoch != current.get('epoch')):
            raise ValueError('La rencontre a changé.')
        recent = [item for item in commentary['events'] if item['id'] <= event_id][-3:]
        context = {
            'score': event['match_score'],
            'clock_seconds': event['clock_seconds'],
            'events': [{key: item[key] for key in ('id', 'kind', 'side', 'frame')} for item in recent],
        }
        return context

    try:
        result = generate_reaction(ARENA.agent, event['kind'], previous, match_context=read_match_context, mode=mode)
        current = (ARENA.latest or {}).get('commentary', {})
        if (session_id != ARENA.session.session_id or session_id != current.get('session_id')
                or epoch != current.get('epoch')):
            return {}
        return {**result, 'tool': {'name': 'get_match_context', 'context': context}}
    except (OSError, RuntimeError, ValueError):
        return {}
    finally:
        CHESTER_MODEL.release()


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, content_type='application/json; charset=utf-8'):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get('Host') in (f'{HOST}:{PORT}', f'localhost:{PORT}')

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {'error': 'Invalid host'})
        if self.path.startswith('/video?session='):
            sid = self.path.split('=', 1)[1]
            if sid != ARENA.session.session_id:
                return self.reply(404, {'error': 'Unknown video session'})
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            sequence = 0
            try:
                while sid == ARENA.session.session_id:
                    current, jpeg = ARENA.session.video_frame()
                    if jpeg and current != sequence:
                        self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(jpeg)).encode()+b'\r\n\r\n'+jpeg+b'\r\n')
                        self.wfile.flush()
                        sequence = current
                    time.sleep(1/60)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            return
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/chester.js': ('chester.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8'),
                 '/assets/stadium-pixel.png': ('assets/stadium-pixel.png', 'image/png'),
                 '/assets/chester.png': ('assets/chester.png', 'image/png'),
                 '/assets/celia.png': ('assets/celia.png', 'image/png'),
                 '/assets/hillman.png': ('assets/hillman.png', 'image/png'),
                 '/assets/team-raimon.png': ('assets/team-raimon.png', 'image/png'),
                 '/assets/team-royal.png': ('assets/team-royal.png', 'image/png'),
                 '/assets/team-occult.png': ('assets/team-occult.png', 'image/png'),
                 '/assets/team-zeus.png': ('assets/team-zeus.png', 'image/png'),
                 '/assets/team-genesis.png': ('assets/team-genesis.png', 'image/png'),
                 '/assets/team-dark-emperors.png': ('assets/team-dark-emperors.png', 'image/png'),
                 '/assets/captain-mark.png': ('assets/captain-mark.png', 'image/png'),
                 '/assets/captain-king.png': ('assets/captain-king.png', 'image/png'),
                 '/assets/captain-talisman.png': ('assets/captain-talisman.png', 'image/png'),
                 '/assets/captain-aphrodite.png': ('assets/captain-aphrodite.png', 'image/png'),
                 '/assets/captain-xene.png': ('assets/captain-xene.png', 'image/png'),
                 '/assets/captain-nathan-dark.png': ('assets/captain-nathan-dark.png', 'image/png'),
                 '/assets/PressStart2P-Regular.ttf': ('assets/PressStart2P-Regular.ttf', 'font/ttf')}
        if self.path not in files:
            return self.reply(404, {'error': 'Not found'})
        name, kind = files[self.path]
        self.reply(200, (WEB / name).read_bytes(), kind)

    def do_POST(self):
        origin = self.headers.get('Origin')
        if not self.valid_host() or origin not in (None, URL, f'http://localhost:{PORT}'):
            return self.reply(403, {'error': 'Invalid origin'})
        if self.headers.get('Content-Type') != 'application/json' or not self.path.startswith('/api/'):
            return self.reply(400, {'error': 'Expected JSON API request'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise ValueError('Request too large or empty')
            arguments = json.loads(self.rfile.read(length))
            if not isinstance(arguments, dict):
                raise ValueError('Expected object')
            operation = self.path[5:]
            result = chester_reaction(**arguments) if operation == 'chester_reaction' else ARENA.call(operation, arguments)
            self.reply(200, result)
        except (ValueError, TypeError) as error:
            self.reply(400, {'error': str(error)})
        except Exception as error:
            self.reply(503, {'error': str(error)})


def main(on_ready=None):
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print('InazumIA : '+URL, flush=True)
    try:
        if on_ready: on_ready()
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        ARENA.stop()
        if ARENA.thread:
            ARENA.thread.join(12)
        ARENA.session.close()


if __name__ == '__main__':
    main()
