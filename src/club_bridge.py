"""Translate bounded native NPC selections into the existing arena bridge."""
import ctypes as C
import struct
from arena_bridge import ArenaBridge
from club_fixtures import FIXTURES, dialogue
from scene_team import inspect_party_memory


class ClubBridge(ArenaBridge):
    def __init__(self, emulator):
        super().__init__(emulator, 'club')
        self.preparing = False

    def poll_frame(self):
        if super().poll_frame(): return True
        if self.preparing or self.fixture: return False
        pointer = self.emulator.lib.retro_get_memory_data(2)
        if not pointer: return False
        base = self.profile['global_base'] - 0x02000000
        flag, = struct.unpack('<I', C.string_at(pointer+base+5*4, 4))
        counter, = struct.unpack('<I', C.string_at(pointer+base+8*4, 4))
        selected, = struct.unpack('<I', C.string_at(pointer+base+15*4, 4))
        if flag == 10500 and counter == 4:
            if selected not in FIXTURES:
                raise ValueError('Affiche du PNJ inconnue')
            home, away, _ = FIXTURES[selected]
            self.preparing = True
            try:
                self.prepare(home, away, dialogue(home, away))
                C.memmove(pointer+base+15*4, struct.pack('<I', 0), 4)
            finally:
                self.preparing = False
        return False

    def state(self):
        result = super().state()
        if not self.fixture and result['native_counter'] == 0:
            # The event is loaded on first interaction, so its SSD signature is
            # intentionally absent while walking around the native room.
            _, memory = self.memory()
            flag, = struct.unpack_from('<I', memory, self.profile['global_base']-0x02000000+20)
            choosing, = struct.unpack_from('<I', memory, self.profile['global_base']-0x02000000+56)
            if flag == 10500: result['phase'] = 'choosing' if choosing else 'club'
            result['party_units'] = [p['unit'] for p in inspect_party_memory(memory) if not p['team_field'] & 0x8000]
        return result
