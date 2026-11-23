"""Translate bounded native NPC selections into the existing arena bridge."""
import ctypes as C
import struct
import uuid
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


class NativeClubBridge(ArenaBridge):
    """Open the existing native Hillman board inside the web worker."""

    def __init__(self, emulator):
        super().__init__(emulator, 'club_web')

    def route_state(self):
        pointer = self.emulator.lib.retro_get_memory_data(2)
        base = self.profile['global_base'] - 0x02000000
        return struct.unpack('<I8xI20xII', C.string_at(pointer + base + 20, 44))

    def open_room(self, boot_commands):
        for command in boot_commands:
            self.emulator.command(command)
            if self.route_state()[0] == 10500:
                break
        else:
            raise RuntimeError('Le local de Hillman n’a pas démarré.')
        self.emulator.command({'frames': 600})

    def route_open(self):
        _, _, active, _ = self.route_state()
        return active == 1

    def poll_frame(self):
        if not self.fixture:
            _, counter, _, opponent = self.route_state()
            matchup = {10: (3, 10), 11: (2, 1)}.get(opponent)
            if counter == 10 and matchup:
                home, away = matchup
                self.fixture = {'id': uuid.uuid4().hex, 'home': home, 'away': away, 'lines': []}
        return super().poll_frame()

    def state(self):
        result = super().state()
        if not self.fixture:
            result['phase'] = 'route' if self.route_open() else 'club'
        return result
