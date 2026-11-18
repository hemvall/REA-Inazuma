"""Self-contained BEBF friendly route, executed entirely by native SSD.

Bank 1 references resolve through 02061330 without an index clamp. These
measured, hash-locked references cover only native player records, team headers
and the current game's descriptor; no general memory-writing API is exposed.
"""
import struct
from ssd import Program, helper_prefix, expression, variable, string, fixed

GLOBAL_BASE=0x020DBEBC
PARTY_BASE=0x020E0300
HOME_HEADER=0x020E889C
MATCH_DESCRIPTOR=0x020E891C


def ram_variable(address):
    if address % 4 or not GLOBAL_BASE <= address < GLOBAL_BASE+0x40000:
        raise ValueError('Native variable outside measured bank')
    return 0x10000+(address-GLOBAL_BASE)//4


def event_pair(ssd,sst,config,teams):
    p=Program(*helper_prefix(ssd,sst))
    text_id=600
    def say(text,question=False):
        nonlocal text_id
        if question:
            p.emit(0x306B,4);p.emit(0x301C,5,1,0,0,0,0)
        else:p.emit(0x301A,1,261,0,1,0,-1)
        row=p.emit(0x301D,string(text,1,text_id));text_id+=1
        if question:row.unknown=0

    def clear_owned():
        for index in reversed(range(132)):
            record=PARTY_BASE+index*0xFC
            occupied=expression(0x700F,variable(ram_variable(record+0xF0)),1)
            own=expression(0x7003,expression(0x700F,variable(ram_variable(record+0x40)),0x80000000),0)
            p.emit(0x6008,expression(0x700F,occupied,own))
            branch=p.emit(0x6001,1,0)
            p.emit(0x403F,expression(0x700F,variable(ram_variable(record+0x64)),0xFFFF))
            p.end(branch)

    def header(team):
        value=bytearray.fromhex(teams[team]['header_hex'])
        struct.pack_into('<H',value,62,team)
        for index,word in enumerate(struct.unpack('<16I',value)):
            p.assign(ram_variable(HOME_HEADER+index*4),word)

    def roster(team):
        p.emit(clear_id);header(team)
        for slot,unit in enumerate(teams[team]['roster'],1):
            if unit:p.emit(0x403E,unit,30,slot)

    # Store the five exploration players through the same native add/remove API.
    # This profile has an isolated new-game roster, not campaign-save support.
    clear_id=0x2000+p.ordinal
    opened=p.function(clear_id)
    clear_owned()
    p.end(opened)
    restore_id=0x2000+p.ordinal
    opened=p.function(restore_id)
    p.emit(clear_id);header(1)
    for slot,unit in enumerate(config['team']['units'],1):p.emit(0x403E,unit,1,slot)
    p.end(opened)

    opened=p.function(0x1023)
    p.emit(0x2019)
    say('Veux-tu ouvrir les routes\\nde matchs amicaux ?',True)
    p.emit(0x3057);p.emit(0x6008,expression(0x4020))
    yes=p.emit(0x6001,1,0)
    p.emit(0x301E)
    # A full temporary side also satisfies the stock route's squad-size check.
    roster(1)
    for team in (1,2,3,10,11):
        p.emit(0x40C9,1,team);p.emit(0x4068,1,team)
    p.emit(0x3005,2);p.emit(0x3005,1)
    p.emit(0x30F5,1);p.emit(0x30F6,1)
    p.emit(0x203E)  # Original route/select/confirm loop from 25030300.
    p.emit(0x6008,expression(0x7003,variable(0x20005),255))
    selected=p.emit(0x6001,1,0)
    # The route loads games.dat itself. Each opponent uniquely identifies the
    # requested home team. The native profile uses a separate Raimon opponent.
    p.assign(0x1000F,expression(0x700F,variable(ram_variable(MATCH_DESCRIPTOR)),0xFFFF))
    for away,home in ((10,3),(11,2)):
        p.emit(0x6008,expression(0x7003,variable(0x1000F),away))
        branch=p.emit(0x6001,1,0)
        roster(home)
        p.end(branch)
    p.emit(0x3013,0,0,1000)
    p.emit(0x3005,1)
    p.emit(0x201F,10)
    p.assign(0x1000A,4)
    p.emit(0x4058,4)
    p.assign(0x1001A,expression(0x40CA,2))
    p.emit(0x4048,expression(0x40CA,2))
    p.emit(0x4016,2)
    p.end(selected)
    p.end(yes)
    p.emit(0x6008,expression(0x7002,expression(0x7003,variable(0x10008),10)))
    cancel=p.emit(0x6001,1,0)
    p.emit(restore_id)
    p.emit(0x301E);p.emit(0x3004,2);p.emit(0x3004,1)
    p.emit(0x201B)
    p.end(cancel);p.end(opened)

    opened=p.function(0x1013,expression(0x700F,
        expression(0x7003,variable(0x1000A),4),
        expression(0x7003,variable(0x10008),10)))
    p.emit(restore_id)
    position = config['exploration']['spawn']
    p.emit(0x305A,expression(0x4045,0),0,*(fixed(v) for v in position))
    p.emit(0x3004,1);p.emit(0x201C)
    say('Belle rencontre !\\nReviens choisir une autre affiche\\nquand tu veux.')
    p.emit(0x301E)
    p.emit(0x4097)
    p.emit(0x201B)
    p.end(opened)
    return p.encode()


def route_data(original):
    """Retain the native 34×72-byte route layout, with two independent matches."""
    if len(original)!=34*72:raise ValueError('Unexpected native route size')
    # Empty records use the native sentinel, never a zero-filled start node.
    data=bytearray(original[-72:]*34)
    root=bytearray(original[:72])
    struct.pack_into('<6H',root,0,0,256,128,96,0,0)
    root[12:32]=b'Amicaux du club'.ljust(20,b'\0')
    root[32:52]=b'Choisis une affiche'.ljust(20,b'\0')
    struct.pack_into('<5H',root,62,1,2,0xFFFF,0xFFFF,0)
    data[:72]=root
    for index,(badge,title,x,y) in enumerate(((513,'Occulte vs Zeus',64,48),(549,'Royal Academy vs Raimon',176,48)),1):
        row=bytearray(original[72:144])
        struct.pack_into('<6H',row,0,1,256+index,x,y,0,badge)
        row[12:38]=title.encode('ascii').ljust(26,b'\0')
        row[38:60]=b'Amicaux du club'.ljust(22,b'\0')
        struct.pack_into('<6H',row,60,499+index,0,0xFFFF,0xFFFF,0xFFFF,0)
        data[index*72:(index+1)*72]=row
    return bytes(data)
