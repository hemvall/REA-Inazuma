"""Capture comparable RAM snapshots from an isolated saved duel."""
import json
import argparse
import ctypes
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from emulator_probe import Emulator
from frame_state import screen_observation

root = Path('build/research')
out = root / 'duel-ram'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compare-candidates', action='store_true')
options = parser.parse_args()
emulator = Emulator('build/arena/arena.nds',
                    'local/tools/melonds-core/melonds_libretro.dll', out)
try:
    emulator.command({'frames': 120})
    emulator.command({'load': str(root / 'field.state'), 'frames': 1})
    screen = screen_observation(emulator.last_frame)
    print(json.dumps(screen), flush=True)
    if screen['name'] not in ('attack_duel', 'defence_duel'):
        raise RuntimeError('The checkpoint does not contain a recognized duel')
    for frames in (2, 6, 12):
        for index, action in enumerate([None, *screen['actions']]):
            emulator.command({'load': str(root / 'field.state'), 'frames': 1})
            touch = action['touch'] if action else None
            emulator.command({'frames': 6, 'touch': [touch['x'], touch['y']] if touch else None})
            emulator.command({'frames': frames,
                              'memory': str(out / f'{frames}-{index}.ram')})
    for frames in (2, 6, 12):
        idle, left, right = [(out / f'{frames}-{index}.ram').read_bytes() for index in range(3)]
        offsets = [i for i in range(0, len(idle), 4)
                   if len({data[i:i+4] for data in (idle, left, right)}) == 3]
        print(f'{frames} frames: {len(offsets)} distinct words, first 32:',
              [hex(0x02000000 + i) for i in offsets[:32]], flush=True)
    if options.compare_candidates:
        candidates = (0x020F9EA4, 0x020F9EB8, 0x021319C8)
        for index, action in enumerate(screen['actions'], 1):
            sample = (out / f'2-{index}.ram').read_bytes()
            point = action['touch']
            for method, addresses in [('idle', ()), ('manual', ()),
                                      *((hex(address), (address,)) for address in candidates),
                                      ('combined', candidates)]:
                emulator.command({'load': str(root / 'field.state'), 'frames': 1})
                pointer = emulator.lib.retro_get_memory_data(2)
                for address in addresses:
                    offset = address - 0x02000000
                    ctypes.memmove(pointer + offset, sample[offset:offset+4], 4)
                inputs = {'touch': [point['x'], point['y']]} if method == 'manual' else {}
                emulator.command({'frames': 6, **inputs})
                digests = []
                for frames in (2, 10, 48, 60):
                    emulator.command({'frames': frames})
                    digests.append(hashlib.sha256(emulator.last_frame[2]).hexdigest()[:12])
                print(json.dumps({'choice': action['name'], 'method': method, 'frames': digests,
                                  'screen': screen_observation(emulator.last_frame)['name']}), flush=True)
finally:
    emulator.lib.retro_unload_game()
    emulator.lib.retro_deinit()
