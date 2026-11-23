"""Bounded execution controller; callers must isolate the native core process."""
from emulator_probe import pointer_coordinates, Emulator


def validate_step(frames, keys, touch):
    if type(frames) is not int or not 1<=frames<=120:raise ValueError('Expected 1..120 frames')
    if not isinstance(keys,list) or any(key not in Emulator.BUTTONS for key in keys):raise ValueError('Invalid keys')
    if touch is not None:
        if not isinstance(touch,(list,tuple)) or len(touch)!=2:raise ValueError('Expected a DS touch point')
        pointer_coordinates(*touch)


def execute_step(emulator, frames, keys, touch, should_stop=None, release=True):
    validate_step(frames,keys,touch)
    should_stop=should_stop or (lambda:False)
    before=emulator.frames
    try:
        emulator.pressed={Emulator.BUTTONS[key] for key in keys}
        emulator.touch=touch
        for _ in range(frames):
            if should_stop():break
            emulator.lib.retro_run()
            emulator.frames+=1
        emulator.pressed=set()
        emulator.touch=None
        if release and (keys or touch is not None) and not should_stop():
            for _ in range(4):
                if should_stop():break
                emulator.lib.retro_run()
                emulator.frames+=1
    finally:
        emulator.pressed=set()
        emulator.touch=None
    return emulator.frames-before


class Controller:
    def __init__(self, emulator, should_stop=None):
        self.emulator = emulator
        self.revision = 0
        self.should_stop = should_stop or (lambda:False)

    def touch_path(self, revision, points):
        """Validate the entire path before acting; keep the stylus down between points."""
        if type(revision) is not int or revision != self.revision:
            raise ValueError('Stale revision')
        if not isinstance(points, list) or not 1 <= len(points) <= 120:
            raise ValueError('Expected 1..120 touch points')
        segments = []
        for point in points:
            if not isinstance(point, dict) or set(point) != {'x', 'y', 'frames'}:
                raise ValueError('Expected x, y, frames')
            pointer_coordinates(point['x'], point['y'])
            frames = point['frames']
            if type(frames) is not int or not 1 <= frames <= 120:
                raise ValueError('Expected 1..120 frames')
            segments.append((point['x'], point['y'], frames))
        if sum(p[2] for p in segments) > 120:
            raise ValueError('Path exceeds 120 frames')
        emulator = self.emulator
        try:
            emulator.pressed = set()
            for x, y, frames in segments:
                emulator.touch = (x, y)
                for _ in range(frames):
                    emulator.lib.retro_run()
                    emulator.frames += 1
                    if self.should_stop():break
                if self.should_stop():break
        finally:
            emulator.touch = None
            emulator.pressed = set()
            self.revision += 1
        # The core must sample the release before a subsequent stroke begins.
        if not self.should_stop():
            for _ in range(4):
                emulator.lib.retro_run()
                emulator.frames += 1
                if self.should_stop():break
        return {'revision': self.revision, 'frame': emulator.frames}
