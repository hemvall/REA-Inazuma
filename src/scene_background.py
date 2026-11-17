"""Native illustrated backgrounds at the measured priority behind message UI."""
from ssd import fixed, string


def show_background(program, asset, transition=False):
    if transition:
        program.emit(0x301E)
        program.emit(0x3005, 1, 15)
        program.emit(0x3009, 0)
    # Ordinary fullscreen priority covers the message window; 25000 is also
    # used by original native MCH sprites and was verified with dialogue live.
    program.emit(0x3008, 0, string(asset), 0, 25000)
    program.emit(0x300F, 0)
    program.emit(0x300E, 0, 1)
    program.emit(0x306A, 0, fixed(1), fixed(1), 1)
    program.emit(0x3004, 1, 20)
    program.emit(0x3002, 45)
