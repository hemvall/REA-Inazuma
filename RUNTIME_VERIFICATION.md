# Runtime verification — 2026-11-17

Current ROM: `build/inazuma_mystery.nds`.
SHA-256: `7a9435be30fea323a5d445d9f91355dd89f9e0bce714ca96954cc0f64d865033`.
Cold boot uses the official DeSmuME libretro core `git 95b4d79`, software
renderer and JIT. No save state from another ROM is used. Runtime evidence is
under `build/scenario-complete/`.

The opening has 44 authored French lines, approximately 587 words in four
sequences. Five minutes is a reading/staging target, excluding football;
the player advances the text, so duration is not fixed.

Observed scene checks:

- Native title, new-game naming and legal notices lead into the new event.
- The original power-on Mobiclip movie `op00` still plays. A button press skips
  it to the title; the authored event is reached through New Game.
- The club sign, technique notebook and old football illustrations appear
  behind named portraits and dialogue on the lower screen.
- Hatch, Aphrodite/Byron and Nathan portraits identify the requested characters.
- All 44 opening lines and all four illustrated sequences advance to the native
  match setup from the same cold boot (`match-setup.png`, frame 24944).
- Native football remains the original first-goal four-a-side event; the squad
  has five players, so this is not a new five-a-side match engine.

Read-only ARM9 RAM verification at the first dialogue confirms exactly five
nonzero occupied player records, all at level 1:

| Player | Native ID | Level |
|---|---:|---:|
| Mark | 1 | 1 |
| Jack | 3 | 1 |
| Daniel Hatch | 29 | 1 |
| Byron Love / Aphrodite | 190 | 1 |
| Nathan, Empereurs noirs | 2430 | 1 |

`team-runtime.json` records the hash, addresses and raw fields. Unitbase record
indices differ from native IDs: unitno.dat maps record28 to Hatch29, record157
to Byron190 and record1589 to Nathan2430. Both named records and actual team
rosters corroborate those mappings. No RAM mutation or cheat is used.
The match-setup RAM dump also retains all five requested players at level 1;
the first four enter the native four-a-side selection and Nathan is in the squad.

Known limitations:

- The upper screen is black during illustrated lower-screen dialogue. The old
  native 3D scenery bug remains unresolved; these are real native illustrations.
- Earlier builds blacked out at native match timeout. A diagnostic bypass
  produced corrupt result graphics and was removed. Final native football
  scripts are unchanged. Result/replay and save/reload are not accepted as
  working; authored result text is present but its return path is experimental.
- Original title, legal notices, tutorials and match introduction remain.
- Existing campaign saves and emulator states are unsupported; use New Game.

Structural validation passes selected archive allocation/non-overlap, all 24
script/text entries, callback/reference/text bindings, the five-player native
chapter recruitment block, both team templates, and unchanged unrelated ROM
resources. The 29 unit tests, exact manifest, byte reversal and xdelta round trip
pass. `build/verification.json` keeps `gameplay_tested: false` because that
command performs structural checks only; bounded runtime evidence is here.

Windows GUI interaction in portable DeSmuME 0.9.13 was not automated. The
launcher targets the same ROM. Testing used the separate libretro API without
Windows application control.

REA 6.9.0 installation was separately verified by MCP initialization and a
255-tool response. REA tools are not exposed in this running chat; local format
parsing and Capstone disassembly supplied the binary evidence above.
