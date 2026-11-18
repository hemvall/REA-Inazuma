"""Hash-locked live SSD/SST bridge for the fixed BEBF arena shell.

All writes target measured native event variables or existing script/text slots.
No arbitrary memory writer is exposed to clients. Preparation is allowed only
while the native event is idle; launch uses its original event-counter guard.
"""
import ctypes as C
import json
import struct
import unicodedata
import uuid
from functools import lru_cache
from pathlib import Path
from nds import read_rom, sha
from scene_team import inspect_party_memory
from frame_state import screen_phase

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def catalogue():
    rom = read_rom(ROOT/'rom/original.nds')
    if sha(rom.data) != '1e67c699a6b3ecfb5230e8c2245746879fab57123277651da74b4cc9b8ba25d3':
        raise ValueError('Unsupported original ROM')
    def resource(path): return rom.data[slice(*rom.files[path])]
    index, blob = resource('data_iz/logic/fr/team.pkh'), resource('data_iz/logic/fr/team.pkb')
    units = resource('data_iz/logic/fr/unitbase.dat')
    names = {struct.unpack_from('<H', units, pos+66)[0]: units[pos:pos+32].split(b'\0')[0].decode('latin1')
             for pos in range(0, len(units), 96)}
    result = []
    for i in range(len(blob)//320):
        key = struct.unpack_from('<I', index, 48+i*4)[0]
        if key not in (3, 10): continue
        row = blob[i*320:(i+1)*320]
        roster = [struct.unpack_from('<H', row, 64+j*8)[0] for j in range(16)]
        captain = struct.unpack_from('<H', row, 46)[0]
        result.append({'id': key, 'name': row[:32].split(b'\0')[0].decode('ascii'),
                       'captain_id': captain, 'captain': names[captain], 'roster': roster,
                       'header_hex': row[:64].hex(),
                       'native_match_id': 52 if key == 3 else 33})
    return result


def occurrences(data, pattern):
    start = 0
    while True:
        start = data.find(pattern, start)
        if start < 0: return
        yield start
        start += len(pattern)


class ArenaBridge:
    def __init__(self, emulator):
        self.emulator = emulator
        folder = ROOT/'build/arena'
        self.profile = json.loads((folder/'profile.json').read_text())
        if sha(Path(emulator.rom_path.decode()).read_bytes()) != self.profile['rom_sha256']:
            raise ValueError('Arena profile/ROM mismatch')
        self.ssd = (folder/'scene.ssd').read_bytes()
        self.sst = (folder/'scene.sst').read_bytes()
        self.teams = {team['id']: team for team in catalogue()}
        self.fixture = None
        self.completed = False

    def poll_frame(self):
        if self.fixture and screen_phase(self.emulator.last_frame)=='result':
            self.completed=True
        return self.completed

    def memory(self):
        pointer = self.emulator.lib.retro_get_memory_data(2)
        size = self.emulator.lib.retro_get_memory_size(2)
        if not pointer or size != 4*1024*1024:
            raise ValueError('Unexpected main RAM domain')
        return pointer, C.string_at(pointer, size)

    def state(self):
        self.poll_frame()
        _, memory = self.memory()
        base = self.profile['global_base']-0x02000000
        flag, = struct.unpack_from('<I', memory, base+5*4)
        counter, = struct.unpack_from('<I', memory, base+8*4)
        result, = struct.unpack_from('<I', memory, base+9*4)
        loaded = self.ssd[:32] in memory
        phase = {0:'idle', 4:'idle', 1:'starting', 2:'dialogue', 10:'playing', 3:'result'}.get(counter, 'unknown')
        if flag != 10500 or not loaded:
            phase = 'booting' if self.fixture is None else ('playing' if counter == 10 else 'loading')
        if self.completed:phase='result'
        elif phase=='playing' and screen_phase(self.emulator.last_frame)=='halftime':phase='halftime'
        players = inspect_party_memory(memory) if phase in ('playing','halftime','result') else []
        return {'phase': phase, 'native_counter': counter,
                'home_units': [p['unit'] for p in players if not p['team_field'] & 0x8000],
                'away_units': [p['unit'] for p in players if p['team_field'] & 0x8000],
                'roster_source':'BEBF native player database at 0x020E0300',
                'native_result':result if phase=='result' and not self.completed else None,
                'result': ('completed' if self.completed else ('victory' if result == 1 else 'not_victory')) if phase == 'result' else None,
                'result_source':'native_final_screen' if self.completed else ('native_callback' if phase=='result' else None),
                'fixture': self.fixture}

    def prepare(self, home, away, lines):
        if home == away or home not in self.teams or away not in self.teams:
            raise ValueError('Unsupported teams')
        if self.state()['phase'] != 'idle':
            raise ValueError('Arena must be idle before preparation')
        if not isinstance(lines, list) or len(lines) != 6:
            raise ValueError('Exactly six dialogue lines required')
        slots = self.profile['slots']
        encoded = []
        for i, line in enumerate(lines):
            if not isinstance(line, str) or not line.strip():
                raise ValueError('Empty dialogue')
            line = line.translate(str.maketrans({'’':"'",'‘':"'",'“':'"','”':'"','«':'"','»':'"','œ':'oe','Œ':'OE','æ':'ae','Æ':'AE','–':'-','—':'-','…':'...','\u00a0':' ','\u202f':' '}))
            normalized = ''.join(c for c in unicodedata.normalize('NFKD', line) if not unicodedata.combining(c))
            if any(ord(c)<32 or ord(c)>126 for c in normalized):
                raise ValueError('Unsupported dialogue characters')
            # Native message escape sequence, at most three 30-character lines.
            import textwrap
            wrapped = textwrap.wrap(normalized, width=30)
            if len(wrapped)>3:
                raise ValueError('Dialogue exceeds three DS text lines')
            text = '\\n'.join(wrapped).encode('ascii')
            capacity = slots['texts'][i]['capacity']
            if len(text)>=capacity: raise ValueError('Dialogue slot overflow')
            encoded.append(text+b'\0'*(capacity-len(text)))
        pointer, memory = self.memory()
        script_bases = list(occurrences(memory, self.ssd[:64]))
        text_bases = [offset-4 for offset in occurrences(memory, self.sst[4:96])]
        if not script_bases or not text_bases:
            raise ValueError('Native arena buffers unavailable')
        writes=[]
        for base in script_bases:
            for slot, unit in zip(slots['roster'], self.teams[home]['roster']):
                writes.append((base+slot, struct.pack('<I', unit)))
            for i, slot in enumerate(slots['portraits']):
                writes.append((base+slot, struct.pack('<I', self.teams[home if i%2==0 else away]['captain_id'])))
            writes.append((base+slots['match'], struct.pack('<I', self.teams[away]['native_match_id'])))
        for base in text_bases:
            for slot, text in zip(slots['texts'], encoded):
                writes.append((base+slot['offset'], text))
        # 0x0206B704 returns team manager +0x17C + side*0x40. The measured
        # manager is 0x020E8720; native loader copies its 64-byte team header.
        header_offset = 0x020E889C-0x02000000
        if memory[header_offset:header_offset+32].split(b'\0')[0] not in (b'Raimon',b'Occulte',b'Zeus'):
            raise ValueError('Native home-team header invariant failed')
        header = bytearray.fromhex(self.teams[home]['header_hex'])
        struct.pack_into('<H',header,62,home)
        writes.append((header_offset,bytes(header)))
        for offset, value in writes:
            if not 0 <= offset <= len(memory)-len(value):
                raise ValueError('Invalid arena buffer bounds')
        for offset, value in writes:
            C.memmove(pointer+offset, value, len(value))
            if C.string_at(pointer+offset,len(value)) != value:
                raise RuntimeError('Arena write verification failed')
        self.fixture = {'id':uuid.uuid4().hex,'home': home, 'away': away, 'lines': lines}
        return {'prepared': True, 'script_buffers': len(script_bases), 'text_buffers': len(text_bases), **self.state()}

    def start(self):
        if not self.fixture or self.state()['native_counter'] != 4:
            raise ValueError('Arena must be waiting with a prepared fixture')
        self.emulator.command({'frames': 2, 'keys': ['A']})
        self.emulator.command({'frames': 120})
        return self.state()
