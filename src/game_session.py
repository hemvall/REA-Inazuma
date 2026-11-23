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
import sys

ROOT = Path(__file__).resolve().parents[1]


def _worker(pipe, rom, core, directory, profile, video=None):
    from emulator_probe import Emulator, png
    from emulator_worker import Controller,validate_step,execute_step
    from match_actions import legal_commands, observe_match
    from chester import MatchCommentary
    emulator = None
    try:
        Path(directory).mkdir(parents=True,exist_ok=True)
        log_fd=os.open(str(Path(directory)/'native.log'),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
        os.dup2(log_fd,1)
        os.dup2(log_fd,2)
        os.close(log_fd)
        # WindowsConsoleIO caches the original console HANDLE, which dup2 closes.
        # Reopen Python streams against the redirected descriptors before the
        # emulator prints its startup message. Native output still uses fd 1/2.
        sys.stdout = open(1, 'w', encoding='utf-8', buffering=1, closefd=False)
        sys.stderr = open(2, 'w', encoding='utf-8', buffering=1, closefd=False)
        emulator = Emulator(rom, core, directory)
        bridge = None
        commentary = MatchCommentary()
        checkpoints = {}
        baseline = None
        live = False
        next_tick = time.monotonic()
        video_frame = -1
        next_video = 0
        last_commentary_frame = -30

        def record_commentary(match, observation):
            nonlocal last_commentary_frame
            commentary.observe(match, observation, bridge.teams)
            last_commentary_frame = emulator.frames

        def sample_commentary():
            if bridge and bridge.fixture and emulator.frames - last_commentary_frame >= 30:
                match = bridge.state()
                record_commentary(match, observe_match(match, emulator.frames, controller.revision))

        def publish_video():
            nonlocal video_frame
            if video is None or emulator.last_frame is None or video_frame == emulator.frames:
                return
            from video_stream import encode_jpeg
            encoded = encode_jpeg(emulator.last_frame)
            with video.get_lock():
                # Four bytes length, eight bytes sequence, then the latest JPEG.
                import struct
                sequence = struct.unpack_from('<Q', video.get_obj(), 4)[0] + 1
                if len(encoded) + 12 > len(video):
                    raise ValueError('Video frame exceeds shared buffer')
                struct.pack_into('<IQ', video.get_obj(), 0, len(encoded), sequence)
                video.get_obj()[12:12+len(encoded)] = encoded
            video_frame = emulator.frames
        def publish_due():
            nonlocal next_video
            if video is None:
                return
            now = time.monotonic()
            if now >= next_video:
                publish_video()
                next_video = now + 1/30

        def on_frame():
            publish_due()
            sample_commentary()
            return bool(bridge and bridge.poll_frame())

        def match_frame_callback(realtime):
            next_frame = time.monotonic()

            def on_match_frame():
                nonlocal next_frame
                publish_due()
                sample_commentary()
                if bridge.poll_match_result():
                    return True
                if realtime:
                    now = time.monotonic()
                    if next_frame > now:
                        time.sleep(next_frame - now)
                    next_frame = max(next_frame + 1/60, time.monotonic())
                return False

            return on_match_frame

        controller = Controller(emulator, on_frame)
        club_return = None
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
            commentary.reset(restored=True)
            if bridge:
                bridge.fixture = fixture
                bridge.completed=False

        if profile in ('arena', 'club'):
            from arena_bridge import ArenaBridge
            from club_bridge import ClubBridge
            bridge = ClubBridge(emulator) if profile == 'club' else ArenaBridge(emulator)
            commands = json.loads((ROOT/'profiles/arena_boot.json').read_text(encoding='utf-8'))
            for command in commands:
                emulator.command(command)
                if (bridge.state()['phase'] == 'club' if profile == 'club' else bridge.state()['native_counter'] == 4):
                    if profile == 'club':
                        emulator.command({'frames':600})
                    break
            if (bridge.state()['phase'] != 'club' if profile == 'club' else bridge.state()['native_counter'] != 4):
                raise RuntimeError('Arena boot failed: waiting dialogue not reached')
            baseline = snapshot()
            club_return = baseline
        pipe.send({'ready': True})
        while True:
            if live and not pipe.poll(max(0, next_tick-time.monotonic())):
                execute_step(emulator, 1, [], None, lambda:bool(bridge and bridge.poll_frame()))
                sample_commentary()
                if emulator.frames % 2 == 0:
                    publish_video()
                if bridge and bridge.completed:
                    live = False
                    publish_video()
                # Drop timing debt on slow machines; never queue old frames.
                next_tick = max(next_tick+1/60, time.monotonic()-1/60)
                continue
            request = pipe.recv()
            try:
                op = request['op']
                if op == 'close':
                    pipe.send({'closed': True})
                    break
                if bridge and not bridge.fixture and bridge.state()['native_counter']==4 and op in ('step','touch_path'):
                    if op=='touch_path' or request.get('keys') or request.get('touch') is not None:
                        raise ValueError('Préparez une rencontre avant de quitter le salon.')
                if op == 'playback':
                    if type(request.get('running')) is not bool:
                        raise ValueError('Expected boolean running')
                    live = request['running'] and not bool(bridge and bridge.completed)
                    next_tick = time.monotonic()
                elif op == 'step':
                    if type(request['revision']) is not int or request['revision'] != controller.revision:
                        raise ValueError('Stale revision')
                    frames = request.get('frames', 1)
                    keys = request.get('keys', [])
                    touch = request.get('touch')
                    validate_step(frames,keys,touch)
                    continuous = request.get('continuous',False)
                    if type(continuous) is not bool: raise ValueError('Expected boolean continuous input')
                    if profile == 'club' and bridge.state()['phase'] == 'club' and ('A' in keys or touch is not None):
                        club_return = snapshot()
                    try:
                        if bridge and bridge.poll_frame():
                            if keys or touch is not None:restore(club_return if profile == 'club' else baseline)
                        else:
                            execute_step(emulator,frames,keys,touch,on_frame,release=not continuous)
                    finally:
                        emulator.pressed = set()
                        emulator.touch = None
                        controller.revision += 1
                elif op in ('observe_match', 'apply_match_action', 'advance_match'):
                    if not bridge or not bridge.fixture:
                        raise ValueError('Préparez une rencontre dans l’arène.')
                    if op != 'observe_match':
                        if live:
                            raise ValueError('Une rencontre en contrôle pas à pas est requise.')
                        revision = request.get('revision')
                        if type(revision) is not int or revision != controller.revision:
                            raise ValueError('Observation périmée.')
                        on_match_frame = match_frame_callback(request.get('realtime') is True)
                        if op == 'apply_match_action':
                            frame = request.get('frame')
                            if type(frame) is not int or frame != emulator.frames:
                                raise ValueError('Observation périmée.')
                            action_id = request.get('action_id')
                            commands = legal_commands(bridge.state())
                            if not isinstance(action_id, str) or action_id not in commands:
                                raise ValueError('Action indisponible pour cet état.')
                            action = commands[action_id]
                            try:
                                if action is None:
                                    execute_step(emulator, 2, ['A'], None, on_match_frame)
                                else:
                                    point = action['touch']
                                    touch = (point['x'], point['y']) if point else None
                                    execute_step(emulator, action['frames'], action['keys'], touch, on_match_frame)
                                    if action.get('settle_frames'):
                                        execute_step(emulator, action['settle_frames'], [], None, on_match_frame)
                            finally:
                                controller.revision += 1
                        else:
                            frames = request.get('frames')
                            validate_step(frames, [], None)
                            try:
                                execute_step(emulator, frames, [], None, on_match_frame)
                            finally:
                                controller.revision += 1
                elif op == 'choose_duel':
                    if not bridge or not bridge.fixture or live:
                        raise ValueError('Une rencontre en contrôle pas à pas est requise.')
                    if (type(request.get('revision')) is not int or request['revision'] != controller.revision
                            or type(request.get('frame')) is not int or request['frame'] != emulator.frames):
                        raise ValueError('Observation périmée.')
                    match = bridge.state()
                    screen = match['screen']
                    if match['phase'] != 'playing' or not screen['requires_tactics']:
                        raise ValueError('Aucun duel reconnu dans l’état courant.')
                    action = next((item for item in screen['actions'] if item['name'] == request.get('choice')), None)
                    if action is None:
                        raise ValueError('Choix indisponible pour ce duel.')
                    touch = action['touch']
                    execute_step(emulator, action['frames'], action['keys'], (touch['x'], touch['y']), on_frame)
                    if action.get('settle_frames'):
                        execute_step(emulator, action['settle_frames'], [], None, on_frame)
                    controller.revision += 1
                elif op == 'touch_path':
                    if bridge and bridge.poll_frame():raise ValueError('Rencontre terminée : utilisez reset_match.')
                    if profile == 'club' and bridge.state()['phase'] == 'club': club_return = snapshot()
                    controller.touch_path(request['revision'], request['points'])
                elif op == 'checkpoint_save':
                    if len(checkpoints) >= 8:
                        raise ValueError('Checkpoint limit reached (8)')
                    checkpoint_id = uuid.uuid4().hex
                    checkpoints[checkpoint_id] = (snapshot(), club_return)
                    pipe.send({'checkpoint_id': checkpoint_id, 'revision': controller.revision})
                    continue
                elif op == 'checkpoint_load':
                    if type(request['revision']) is not int or request['revision'] != controller.revision:
                        raise ValueError('Stale revision')
                    saved, club_return = checkpoints[request['checkpoint_id']]
                    restore(saved)
                    controller.revision += 1
                elif op in ('prepare_match','start_match','reset_match'):
                    if not bridge:
                        raise ValueError('Session is not an arena')
                    if type(request['revision']) is not int or request['revision'] != controller.revision:
                        raise ValueError('Stale revision')
                    if op == 'reset_match':
                        restore(club_return if profile == 'club' else baseline)
                    elif op == 'prepare_match':
                        if profile == 'club': raise ValueError('Choisissez votre affiche en parlant au PNJ.')
                        bridge.prepare(request['home'],request['away'],request['lines'])
                    else:
                        bridge.start()
                    controller.revision += 1
                elif op != 'observe':
                    raise ValueError('Unknown operation')
                result = {'revision': controller.revision, 'frame': emulator.frames}
                publish_video()
                if bridge:
                    result['match'] = bridge.state()
                    observation = observe_match(result['match'], emulator.frames, controller.revision)
                    record_commentary(result['match'], observation)
                    result['commentary'] = commentary.snapshot()
                if op in ('observe_match', 'apply_match_action', 'advance_match'):
                    result['match_observation'] = observation
                if emulator.last_frame:
                    image_bytes = None
                    if request.get('include_image', True):
                        target = Path(directory) / 'frame.png'
                        png(target, *emulator.last_frame)
                        image_bytes = target.read_bytes()
                        result['image'] = base64.b64encode(image_bytes).decode('ascii')
                    # Keep the native result proof even when the player needs
                    # only compact text. It is not sent to the model.
                    if bridge and bridge.completed:
                        proof=Path(directory)/('result-'+bridge.fixture['id']+'.png')
                        if not proof.exists():
                            if image_bytes is not None:proof.write_bytes(image_bytes)
                            else:png(proof,*emulator.last_frame)
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
    def __init__(self, *, stream_video=True):
        self.lock = threading.RLock()
        self.process = None
        self.pipe = None
        self.session_id = None
        self.identity = None
        self.owner = 'human'
        self.profile = None
        self.video = None
        self.stream_video = stream_video

    def video_frame(self):
        """Read the latest JPEG without waiting for emulator command IPC."""
        video = self.video
        if video is None:
            return 0, b''
        import struct
        with video.get_lock():
            length, sequence = struct.unpack_from('<IQ', video.get_obj())
            return sequence, bytes(video.get_obj()[12:12+length])

    def open(self, profile='scenario', cancel=None):
        with self.lock:
            if profile not in ('scenario','arena','club'):
                raise ValueError('Unknown session profile')
            if self.process and self.process.is_alive():
                if profile != self.profile:
                    raise ValueError('Close the current session before changing profile')
                return {'session_id': self.session_id,'profile':self.profile, **self.identity}
            self.close()
            if profile in ('arena', 'club'):
                from prepare_arena import ensure_built
                ensure_built(profile)
            rom = ROOT / (f'build/{profile}/arena.nds' if profile in ('arena','club') else 'build/inazuma_mystery.nds')
            core = ROOT / 'local/tools/melonds-core/melonds_libretro.dll'
            if not rom.is_file() or not core.is_file():
                raise ValueError('ROM ou cœur melonDS manquant. Voir README.md.')
            self.identity = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                             for name, path in [('rom_sha256', rom), ('core_sha256', core)]}
            if profile in ('arena','club'):
                expected=json.loads((ROOT/f'build/{profile}/profile.json').read_text())
                if expected.get('core_sha256',self.identity['core_sha256']) != self.identity['core_sha256']:
                    raise ValueError('Cœur melonDS incompatible avec le profil validé de cette arène.')
            self.session_id = uuid.uuid4().hex
            self.profile = profile
            self.owner = 'human'
            directory = ROOT / 'build/sessions' / self.session_id
            parent, child = mp.get_context('spawn').Pipe()
            self.pipe = parent
            self.video = mp.get_context('spawn').Array('B', 512*1024) if self.stream_video else None
            self.process = mp.get_context('spawn').Process(
                target=_worker, args=(child, str(rom), str(core), str(directory),profile,self.video), daemon=True)
            self.process.start()
            child.close()
            try:
                result = self._receive(120 if profile in ('arena','club') else 30,cancel)
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
            if op not in ('observe', 'observe_match') and actor != self.owner:
                raise ValueError('Contrôle détenu par ' + self.owner)
            self.pipe.send({'op': op, **arguments})
            result = self._receive(15)
            if 'commentary' in result:
                result['commentary']['session_id'] = session_id
            return result

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
            self.video = None
