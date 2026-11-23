"""Translate bounded native NPC selections into the existing arena bridge."""
import ctypes as C
import struct
import uuid
from arena_bridge import ArenaBridge, occurrences
from club_fixtures import CLUB_FIXTURE, FIXTURES, dialogue
from club_scene import RECRUIT_LEVEL, RECRUIT_SLOT, RECRUIT_UNIT
from emulator_worker import execute_step
from recruitment_rom import FIRST_RECRUIT_ID, encode_name, recruitment_squad
from scene_team import inspect_party_memory


class ClubBridge(ArenaBridge):
    def __init__(self, emulator, *, rom_sha256=None):
        super().__init__(emulator, 'club', rom_sha256=rom_sha256)
        self.preparing = False
        self.recruits = []

    def register_recruit(self, level):
        """Run the native add command in the Club event.

        The caller must have loaded the isolated recruitment ROM and must
        restore its prior checkpoint on failure, including failed interaction.
        """
        state = self.state()
        if state['phase'] != 'club' or self.fixture:
            raise ValueError('Reviens au local avant de recruter.')
        if type(level) is not int or not 1 <= level <= 99:
            raise ValueError('Le niveau doit être compris entre 1 et 99.')
        party = state['party_units']
        if FIRST_RECRUIT_ID in party:
            raise ValueError('Cette recrue fait déjà partie du Club.')
        if len(party) >= 16:
            raise ValueError('L’effectif jouable du Club est complet.')
        pointer, memory = self.memory()
        base = self.profile['global_base'] - 0x02000000
        values = {RECRUIT_UNIT: FIRST_RECRUIT_ID, RECRUIT_LEVEL: level, RECRUIT_SLOT: len(party) + 1}
        addresses = {base + 4 * (variable - 0x10000): value for variable, value in values.items()}
        if any(memory[address:address + 4] != bytes(4) for address in addresses):
            raise ValueError('Le local traite déjà une action de recrutement.')
        try:
            for address, value in addresses.items():
                C.memmove(pointer + address, struct.pack('<I', value), 4)
            execute_step(self.emulator, 2, ['A'], None)
            execute_step(self.emulator, 120, [], None)
            after = self.state()
            _, memory = self.memory()
            owned = [row for row in inspect_party_memory(memory) if not row['team_field'] & 0x8000]
            if (after['phase'] != 'club'
                    or [row['unit'] for row in owned] != [*party, FIRST_RECRUIT_ID]
                    or owned[-1]['level'] != level):
                raise ValueError('Inscription native non confirmée. Place-toi devant le coach.')
            return owned[-1]
        finally:
            for address in addresses:
                C.memset(pointer + address, 0, 4)

    def verify_recruit(self, draft):
        _, memory = self.memory()
        records = [row for row in inspect_party_memory(memory)
                   if row['unit'] == FIRST_RECRUIT_ID and not row['team_field'] & 0x8000]
        names = encode_name(draft['name']) + encode_name(draft['short_name'])
        matching = [position for position in occurrences(memory, names)
                    if position + 96 <= len(memory)
                    and struct.unpack_from('<H', memory, position + 66)[0] == FIRST_RECRUIT_ID]
        if len(records) != 1 or records[0]['level'] != draft['level'] or not matching:
            raise ValueError('Le nom, le niveau ou l’identifiant natif de la recrue diffère de la fiche.')
        name, short_name = (memory[matching[0] + offset:matching[0] + offset + 32]
                            .split(b'\0', 1)[0].decode('ascii') for offset in (0, 32))
        return {'unit': FIRST_RECRUIT_ID, 'name': name, 'short_name': short_name,
                'level': records[0]['level'], 'team_id': draft['team_id']}

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
            if selected not in FIXTURES and selected != CLUB_FIXTURE:
                raise ValueError('Affiche du PNJ inconnue')
            self.preparing = True
            try:
                if selected == CLUB_FIXTURE:
                    self.prepare_club_fixture()
                else:
                    home, away, _ = FIXTURES[selected]
                    self.prepare(home, away, dialogue(home, away))
                C.memmove(pointer+base+15*4, struct.pack('<I', 0), 4)
            finally:
                self.preparing = False
        return False

    def prepare_club_fixture(self):
        squad = [(row['unit'], row['level']) for row in inspect_party_memory(self.memory()[1])
                 if not row['team_field'] & 0x8000]
        units = {unit for unit, _ in squad}
        if FIRST_RECRUIT_ID not in units or len(squad) > 16:
            raise ValueError('L’effectif du Club ne peut pas être aligné.')
        home = self.recruits[-1]['team_id']
        away = 1 if home == 10 else 10
        if len(self.recruits) == 1 and home == 1:
            # Keep the Club party and fill the starting eleven with Raimon players.
            guests = [(unit, 30) for unit in self.teams[home]['roster'] if unit and unit not in units]
            squad.extend(guests[:max(0, 11 - len(squad))])
        else:
            squad = recruitment_squad(self.teams[home]['roster'], home, self.recruits)
        self.prepare(home, away, dialogue(home, away), club_squad=squad)

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
