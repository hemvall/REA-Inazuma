# Five-player new-game initialization

`src/scene_team.py` changes the early-game team template at
`data_iz/logic01/fr/team.pkb` and `data_iz/logic/fr/team.pkb`, fixed record key 1
(Raimon). Their original rosters contain Mark alone and twelve Raimon players,
respectively. Native chapter startup rebuilds the squad from the general library,
so both templates must agree. The chapter also executes an explicit remove/add
sequence (instructions 2585–2608, opcodes `0x403F` and `0x403E`) rebuilding the
original twelve players. `isolate_first_chapter_roster` replaces the removals
and excess additions with zero-frame waits and registers the five requested
units through the original addition command, retaining instruction IDs and
updating binary sizes.
The new roster contains Mark, Jack, Daniel Hatch, Byron Love
and Nathan from the Empereurs noirs, with native base level 1 and zero level
offsets. This is a roster template edit, separate from cutscene actor creation.

The source ROM is the hash-locked French BEBF revision 0. These findings come
from local ROM parsing and Capstone ARM disassembly; they are not REA Evidence.

Static chain:

- New-game overlay 3 at `0x02103224`–`0x02103240` calls native team loading at
  `0x01FFC738` with side 0, team key 1, base level 1.
- The loader calls `0x01FFC328`. That function walks 32 eight-byte entries from
  team-record offset `0x40`, reads the unit as a 16-bit value, and reads its
  party/formation positions at bytes 2 and 3.
- At `0x01FFC4A4`–`0x01FFC4B0` it adds entry byte 4 to the base level.
- `0x01FFDE10` passes the resulting level into player creation. The native level
  setter `0x0207FE60` clamps it to 1–99; current level is read from record byte
  `0xAA` at `0x0207FE88`.
- Player records are allocated from database `0x020E0300` in `0xFC`-byte
  records, confirmed by `0x02035980`; each record's unit is stored at offset
  `0x64` (`0x01FFDCAC`) and occupancy is bit 0 of offset `0xF0`.

Character identity is checked against named 96-byte `unitbase.dat` records and
the native ID mapping in `unitno.dat`. A record index is not a native unit ID:
the native IDs are Mark 1, Jack 3, Hatch 29, Byron 190 and Dark Nathan 2430,
corresponding to records 1, 3, 28, 157 and 1589. The mapping is also present at
unitbase record offset 66. Nathan's record 1589 has team association byte 65
equal to 41. In the fixed-record
team archive, key 41 is named `Empereurs noirs`. Normal Nathan is unit 2 and has
team association 1. Byron is native unit 190 and his short display name is Aphrodite.

`inspect_party_memory` provides read-only parsing of an ARM9 emulator memory dump
to validate actual initialized units and levels. Static template checks alone do
not establish that the final ROM created the roster; runtime acceptance belongs
in `RUNTIME_VERIFICATION.md` with the exact tested ROM hash.
