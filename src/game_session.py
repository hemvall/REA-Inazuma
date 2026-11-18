"""Isolated melonDS process with a dedicated Pipe, never native stdout as IPC."""
import base64
import hashlib
import multiprocessing as mp
from pathlib import Path
import threading
import uuid
import ctypes as C
import json
import time
import os

ROOT = Path(__file__).resolve().parents[1]


def _worker(pipe, rom, core, directory, profile):
    from emulator_probe import Emulator, png
    from emulator_worker import Controller,validate_step,execute_step
    emulator = None
    try:
        Path(directory).mkdir(parents=True,exist_ok=True)
        log_fd=os.open(str(Path(directory)/'native.log'),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        os.dup2(log_fd,1)
        os.dup2(log_fd,2)
        os.close(log_fd)
        emulator = Emulator(rom, core, directory)
        bridge = None
        controller = Controller(emulator,lambda:bool(bridge and bridge.poll_frame()))
        checkpoints = {}
        baseline = None
        def snapshot():
            size = emulator.lib.retro_serialize_size()
            if not 0 < size <= 128*1024*1024:
                raise ValueError('Invalid checkpoint size')
            buffer = C.create_string_buffer(size)
            if not emulator.lib.retro_serialize(buffer,size):
                raise RuntimeError('Checkpoint save failed')
            import copy
            return buffer.raw,emulator.frames,emulator.last_frame,copy.deepcopy(bridge.fixture) if bridge else None

        def restore(value):
            state,frames,image,fixture = value
            buffer = C.create_string_buffer(state)
            if not emulator.lib.retro_unserialize(buffer,len(state)):
                raise RuntimeError('Checkpoint restore failed; close session')
            emulator.frames,emulator.last_frame = frames,image
            emulator.pressed,emulator.touch = set(),None
            if bridge:
                bridge.fixture = fixture
                bridge.completed=False

        if profile == 'arena':
            from arena_bridge import ArenaBridge
            bridge = ArenaBridge(emulator)
            commands = json.loads((ROOT/'profiles/arena_boot.json').read_text(encoding='utf-8'))
            for command in commands:
                emulator.command(command)
                if bridge.state()['native_counter'] == 4:
                    emulator.command({'frames':600})
                    break
            if bridge.state()['native_counter'] != 4:
                raise RuntimeError('Arena boot failed: waiting dialogue not reached')
            baseline = snapshot()
        pipe.send({'ready': True})
        while True:
            request = pipe.recv()
            try:
                op = request['op']
                if op == 'close':
                    pipe.send({'closed': True})
                    break
                if bridge and not bridge.fixture and bridge.state()['native_counter']==4 and op in ('step','touch_path'):
                    if op=='touch_path' or request.get('keys') or request.get('touch') is not None:
                        raise ValueError('Préparez une rencontre avant de quitter le salon.')
                if op == 'step':
                    if type(request['revision']) is not int or request['revision'] != controller.revision:
                        raise ValueError('Stale revision')
                    frames = request.get('frames', 1)
                    keys = request.get('keys', [])
                    touch = request.get('touch')
                    validate_step(frames,keys,touch)
                    try:
                        if bridge and bridge.poll_frame():
                            if keys or touch is not None:restore(baseline)
                        else:
                            execute_step(emulator,frames,keys,touch,lambda:bool(bridge and bridge.poll_frame()))
                    finally:
                        emulator.pressed = set()
                        emulator.touch = None
                        controller.revision += 1
                elif op == 'touch_path':
                    if bridge and bridge.poll_frame():raise ValueError('Rencontre terminée : utilisez reset_match.')
                    controller.touch_path(request['revision'], request['points'])
                elif op == 'checkpoint_save':
                    if len(checkpoints) >= 8:
                        raise ValueError('Checkpoint limit reached (8)')
                    checkpoint_id = uuid.uuid4().hex
                    checkpoints[checkpoint_id] = snapshot()
                    pipe.send({'checkpoint_id': checkpoint_id, 'revision': controller.revision})
                    continue
                elif op == 'checkpoint_load':
                    if type(request['revision']) is not int or request['revision'] != controller.revision:
                        raise ValueError('Stale revision')
                    restore(checkpoints[request['checkpoint_id']])
                    controller.revision += 1
                elif op in ('prepare_match','start_match','reset_match'):
                    if not bridge:
                        raise ValueError('Session is not an arena')
                    if type(request['revision']) is not int or request['revision'] != controller.revision:
                        raise ValueError('Stale revision')
                    if op == 'reset_match':
                        restore(baseline)
                    elif op == 'prepare_match':
                        bridge.prepare(request['home'],request['away'],request['lines'])
                    else:
                        bridge.start()
                    controller.revision += 1
                elif op != 'observe':
                    raise ValueError('Unknown operation')
                result = {'revision': controller.revision, 'frame': emulator.frames}
                if bridge:
                    result['match'] = bridge.state()
                if emulator.last_frame:
                    target = Path(directory) / 'frame.png'
                    png(target, *emulator.last_frame)
                    result['image'] = base64.b64encode(target.read_bytes()).decode('ascii')
                    if bridge and bridge.completed:
                        proof=Path(directory)/('result-'+bridge.fixture['id']+'.png')
                        if not proof.exists():proof.write_bytes(target.read_bytes())
                with (Path(directory)/'replay.jsonl').open('a',encoding='utf-8') as log:
                    log.write(json.dumps({'request':request,'result':{k:v for k,v in result.items() if k!='image'}},ensure_ascii=False)+'\n')
                pipe.send(result)
            except Exception as error:
                pipe.send({'error': str(error), 'revision': controller.revision})
    except (EOFError, BrokenPipeError):
        pass
    except Exception as error:
        pipe.send({'error': str(error)})
    finally:
        if emulator:
            emulator.lib.retro_unload_game()
            emulator.lib.retro_deinit()
        pipe.close()


class GameSession:
    def __init__(self):
        self.lock = threading.RLock()
        self.process = None
        self.pipe = None
        self.session_id = None
        self.identity = None
        self.owner = 'human'
        self.profile = None

    def open(self, profile='scenario', cancel=None):
        with self.lock:
            if profile not in ('scenario','arena'):
                raise ValueError('Unknown session profile')
            if self.process and self.process.is_alive():
                if profile != self.profile:
                    raise ValueError('Close the current session before changing profile')
                return {'session_id': self.session_id,'profile':self.profile, **self.identity}
            self.close()
            rom = ROOT / ('build/arena/arena.nds' if profile=='arena' else 'build/inazuma_mystery.nds')
            core = ROOT / 'local/tools/melonds-core/melonds_libretro.dll'
            if not rom.is_file() or not core.is_file():
                raise ValueError('ROM ou cœur melonDS manquant. Voir README.md.')
            self.identity = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                             for name, path in [('rom_sha256', rom), ('core_sha256', core)]}
            if profile=='arena':
                expected=json.loads((ROOT/'build/arena/profile.json').read_text())
                if expected.get('core_sha256',self.identity['core_sha256']) != self.identity['core_sha256']:
                    raise ValueError('Cœur melonDS incompatible avec le profil validé de cette arène.')
            self.session_id = uuid.uuid4().hex
            self.profile = profile
            self.owner = 'human'
            directory = ROOT / 'build/sessions' / self.session_id
            parent, child = mp.get_context('spawn').Pipe()
            self.pipe = parent
            self.process = mp.get_context('spawn').Process(
                target=_worker, args=(child, str(rom), str(core), str(directory),profile), daemon=True)
            self.process.start()
            child.close()
            try:
                result = self._receive(120 if profile=='arena' else 30,cancel)
                if 'error' in result:
                    raise RuntimeError(result['error'])
            except Exception:
                self.close()
                raise
            return {'session_id': self.session_id,'profile':self.profile, **self.identity}

    def _receive(self, timeout, cancel=None):
        deadline = time.monotonic()+timeout
        while not self.pipe.poll(.1):
            if cancel and cancel.is_set():
                self.close()
                raise RuntimeError('Ouverture annulée')
            if time.monotonic() >= deadline:
                self.close()
                raise TimeoutError('Worker timeout; session stopped')
        try:
            return self.pipe.recv()
        except (EOFError,OSError) as error:
            self.close()
            raise RuntimeError('Le worker melonDS s’est arrêté. Consultez build/sessions/ puis rouvrez une session.') from error

    def request(self, session_id, op, actor='human', **arguments):
        with self.lock:
            if session_id != self.session_id or not self.process or not self.process.is_alive():
                raise ValueError('Session inconnue ou arrêtée')
            if op != 'observe' and actor != self.owner:
                raise ValueError('Contrôle détenu par ' + self.owner)
            self.pipe.send({'op': op, **arguments})
            return self._receive(15)

    def set_control(self, session_id, owner):
        with self.lock:
            if owner not in ('human', 'agent') or session_id != self.session_id or not self.process:
                raise ValueError('Contrôle ou session invalide')
            self.owner = owner
            return {'owner': owner}

    def close(self):
        with self.lock:
            if self.process:
                if self.process.is_alive():
                    try:
                        self.pipe.send({'op': 'close'})
                        self.process.join(2)
                    except (OSError, EOFError):
                        pass
                    if self.process.is_alive():
                        self.process.terminate()
                        self.process.join(2)
                self.process.close()
            if self.pipe:
                self.pipe.close()
            self.process = self.pipe = self.session_id = None
