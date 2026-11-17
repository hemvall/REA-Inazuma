"""Minimal software-only libretro test host; does not automate Windows apps.

Reads JSON commands from stdin and writes emulator framebuffer PNGs and optional
private test states under build/. Uses the official libretro C ABI via ctypes.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import struct
import sys
import time
import zlib


class Variable(C.Structure):
    _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]


class GameInfo(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]


class SystemInfo(C.Structure):
    _fields_ = [('name', C.c_char_p), ('version', C.c_char_p), ('extensions', C.c_char_p), ('fullpath', C.c_bool), ('block_extract', C.c_bool)]


def png(path, width, height, pixels, pitch, pixel_format):
    rows = []
    for y in range(height):
        raw = pixels[y*pitch:(y+1)*pitch]
        if pixel_format == 1:
            rgb = bytes(component for x in range(width) for component in (raw[x*4+2], raw[x*4+1], raw[x*4]))
        else:
            values = struct.unpack_from('<'+'H'*width, raw)
            if pixel_format == 2:
                rgb = bytes(component for v in values for component in (((v>>11)&31)*255//31, ((v>>5)&63)*255//63, (v&31)*255//31))
            else:
                rgb = bytes(component for v in values for component in (((v>>10)&31)*255//31, ((v>>5)&31)*255//31, (v&31)*255//31))
        rows.append(b'\0'+rgb)

    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data)&0xFFFFFFFF)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))+chunk(b'IDAT', zlib.compress(b''.join(rows)))+chunk(b'IEND', b''))


class Emulator:
    BUTTONS = {'B': 0, 'Y': 1, 'SELECT': 2, 'START': 3, 'UP': 4, 'DOWN': 5,
               'LEFT': 6, 'RIGHT': 7, 'A': 8, 'X': 9, 'L': 10, 'R': 11}

    def __init__(self, rom, core, directory, frame_skip=0):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.directory_bytes = str(self.directory).encode()
        self.options = {
            b'desmume_cpu_mode': b'jit', b'desmume_opengl_mode': b'disabled',
            b'desmume_jit_block_size': b'100',
            b'desmume_use_external_bios': b'disabled', b'desmume_boot_into_bios': b'disabled',
            b'desmume_firmware_language': b'French', b'desmume_screens_layout': b'top/bottom',
            b'desmume_pointer_type': b'touch', b'desmume_frameskip': b'0',
            b'desmume_num_cores': b'1'}
        self.pixel_format = 0
        self.options[b'desmume_frameskip'] = str(frame_skip).encode('ascii')
        self.last_frame = None
        self.pressed = set()
        self.touch = None
        self.frames = 0
        self.lib = C.CDLL(str(Path(core).resolve()))
        self.callbacks = []

        def callback(restype, *args):
            def decorate(func):
                instance = C.CFUNCTYPE(restype, *args)(func)
                self.callbacks.append(instance)
                return instance
            return decorate

        @callback(None, C.c_int, C.c_char_p)
        def log(level, message):
            if level >= 3:
                print('CORE: '+message.decode(errors='replace'), file=sys.stderr, flush=True)

        @callback(C.c_bool, C.c_uint, C.c_void_p)
        def environment(command, data):
            if command in (9, 31):
                C.cast(data, C.POINTER(C.c_char_p))[0] = self.directory_bytes
                return True
            if command == 10:
                self.pixel_format = C.cast(data, C.POINTER(C.c_int))[0]
                return self.pixel_format in (0, 1, 2)
            if command == 15:
                var = C.cast(data, C.POINTER(Variable)).contents
                if var.key in self.options:
                    var.value = self.options[var.key]
                    return True
                return False
            if command == 16:
                variables = C.cast(data, C.POINTER(Variable))
                i = 0
                while variables[i].key:
                    key, value = variables[i].key, variables[i].value
                    if key not in self.options:
                        self.options[key] = value.split(b'; ', 1)[-1].split(b'|')[0]
                    i += 1
                return True
            if command == 17:
                C.cast(data, C.POINTER(C.c_bool))[0] = False
                return True
            if command == 27:
                C.cast(data, C.POINTER(C.c_void_p))[0] = C.cast(log, C.c_void_p).value
                return True
            if command == 39:
                C.cast(data, C.POINTER(C.c_uint))[0] = 2
                return True
            if command == 52:
                C.cast(data, C.POINTER(C.c_uint))[0] = 0
                return True
            return command in (1, 6, 11, 18, 35, 37)

        @callback(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
        def video(data, width, height, pitch):
            if data and data != C.c_void_p(-1).value:
                self.last_frame = (width, height, C.string_at(data, pitch*height), pitch, self.pixel_format)

        @callback(None, C.c_int16, C.c_int16)
        def audio(left, right):
            pass

        @callback(C.c_size_t, C.c_void_p, C.c_size_t)
        def audio_batch(data, frames):
            return frames

        @callback(None)
        def poll():
            pass

        @callback(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)
        def input_state(port, device, index, ident):
            if device == 1:
                return int(ident in self.pressed)
            if device == 6 and self.touch is not None:
                # Pointer coordinates cover the combined 256x384 framebuffer.
                x, y = self.touch
                if ident == 0:
                    return round(x/255*65534-32767)
                if ident == 1:
                    return round((y+192)/383*65534-32767)
                if ident == 2:
                    return 1
            return 0

        for name, cb in [('environment', environment), ('video_refresh', video),
                         ('audio_sample', audio), ('audio_sample_batch', audio_batch),
                         ('input_poll', poll), ('input_state', input_state)]:
            func = getattr(self.lib, 'retro_set_'+name)
            func.argtypes = [type(cb)]
            func(cb)
        self.lib.retro_get_system_info.argtypes = [C.POINTER(SystemInfo)]
        info = SystemInfo()
        self.lib.retro_get_system_info(C.byref(info))
        self.lib.retro_init()
        self.lib.retro_load_game.argtypes = [C.POINTER(GameInfo)]
        self.lib.retro_load_game.restype = C.c_bool
        self.rom_path = str(Path(rom).resolve()).encode()
        self.rom_data = None if info.fullpath else C.create_string_buffer(Path(rom).read_bytes())
        game = GameInfo(self.rom_path, C.cast(self.rom_data, C.c_void_p) if self.rom_data else None,
                        C.sizeof(self.rom_data)-1 if self.rom_data else 0, None)
        if not self.lib.retro_load_game(C.byref(game)):
            raise RuntimeError('Core rejected ROM')
        self.lib.retro_serialize_size.restype = C.c_size_t
        self.lib.retro_serialize.argtypes = [C.c_void_p, C.c_size_t]
        self.lib.retro_serialize.restype = C.c_bool
        self.lib.retro_unserialize.argtypes = [C.c_void_p, C.c_size_t]
        self.lib.retro_unserialize.restype = C.c_bool
        self.lib.retro_get_memory_data.argtypes = [C.c_uint]
        self.lib.retro_get_memory_data.restype = C.c_void_p
        self.lib.retro_get_memory_size.argtypes = [C.c_uint]
        self.lib.retro_get_memory_size.restype = C.c_size_t
        print(json.dumps({'ready': True, 'core': info.name.decode(), 'version': info.version.decode(), 'fullpath': info.fullpath}), flush=True)

    def command(self, data):
        before = time.monotonic()
        if 'load' in data:
            state = Path(data['load']).read_bytes()
            buffer = C.create_string_buffer(state)
            if not self.lib.retro_unserialize(buffer, len(state)):
                raise RuntimeError('State load failed')
        self.pressed = {self.BUTTONS[x.upper()] for x in data.get('keys', [])}
        self.touch = data.get('touch')
        count = data.get('frames', 0)
        for _ in range(count):
            self.lib.retro_run()
        self.frames += count
        self.pressed = set()
        self.touch = None
        if 'capture' in data:
            if self.last_frame is None:
                raise RuntimeError('No software video frame')
            png(data['capture'], *self.last_frame)
        if 'save' in data:
            size = self.lib.retro_serialize_size()
            buffer = C.create_string_buffer(size)
            if not self.lib.retro_serialize(buffer, size):
                raise RuntimeError('State save failed')
            Path(data['save']).write_bytes(buffer.raw)
        if 'memory' in data:
            ident = data.get('memory_id', 2)
            size = self.lib.retro_get_memory_size(ident)
            pointer = self.lib.retro_get_memory_data(ident)
            if not pointer or not size:
                raise RuntimeError('Memory unavailable')
            Path(data['memory']).write_bytes(C.string_at(pointer, size))
        return {'frames': self.frames, 'elapsed': round(time.monotonic()-before, 3),
                'capture': data.get('capture')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom')
    parser.add_argument('--core', default='local/tools/libretro/desmume_libretro.dll')
    parser.add_argument('--directory', default='build/emulator')
    parser.add_argument('--commands', help='Optional JSONL input sequence instead of interactive stdin')
    parser.add_argument('--frame-skip', type=int, choices=range(10), default=0)
    args = parser.parse_args()
    emulator = Emulator(args.rom, args.core, args.directory, args.frame_skip)
    stream = open(args.commands, encoding='utf-8') if args.commands else sys.stdin
    for line in stream:
        try:
            command = json.loads(line)
            if command.get('quit'):
                break
            print(json.dumps(emulator.command(command)), flush=True)
        except Exception as error:
            print(json.dumps({'error': str(error)}), flush=True)
    emulator.lib.retro_unload_game()
    emulator.lib.retro_deinit()


if __name__ == '__main__':
    main()
