"""Bounded execution controller; callers must isolate the native core process."""
from emulator_probe import pointer_coordinates


class Controller:
    def __init__(self, emulator):
        self.emulator = emulator
        self.revision = 0

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
        finally:
            emulator.touch = None
            emulator.pressed = set()
            self.revision += 1
        # The core must sample the release before a subsequent stroke begins.
        for _ in range(4):
            emulator.lib.retro_run()
            emulator.frames += 1
        return {'revision': self.revision, 'frame': emulator.frames}
