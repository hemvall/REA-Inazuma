# Runtime verification — 2026-11-17

> Document historique. Voir le [index des vérifications actuelles](VERIFICATION.md).

## Latest regular-challenge checkpoint

Native result/XP scripts are restored unchanged; the early return bypass has
been removed. The challenge now uses regular mode 2 and returns through the
chapter's native restoration callback. A shortened-opening diagnostic run
reached the defeat conversation and resumed free movement afterward.
Victory, the XP menu and its following scene are still being verified. This
checkpoint must not be described as full victory/XP acceptance.
All 42 tests passed during this work. Earlier build evidence follows.

## Previous native staging build

ROM: `build/inazuma_mystery.nds`.
SHA-256: `8be90b93eadc816c79f4658adcd6b9d0275ad2015ffb32b1b6621800dc49f14b`.
Tested with melonDS Libretro 0.9.3 `4081e83`, software rendering.

Observed on this exact ROM:

- Cold boot, new game and entrance-object interaction reach a native black fade.
- Controlled Mark is retained and walks to his position. Jack, Hatch, Byron and
  Nathan enter the frame from the path and walk into formation in staggered
  native child threads; all settle before the first dialogue.
- Screenshots `build/staging/gather-6.png`, `gather-9.png` and `settled.png`
  show arrival, formation and the first readable message.
- Advancing all 44 opening lines reaches the native opponent arrival effect.
- `build/staging/enemy-8.png` records the white ramp, `enemy-10.png` and
  `enemy-11.png` the fully white lower screen, and `enemy-13.png` all four
  opponents visible with the first reveal message. Their creation is under white.
- The native sound bank 2D_170 and effect 770 are played at the start of the flash.
  A stereo 32768 Hz PCM capture, `build/staging/enemy-arrival.wav`, contains
  647716 bytes of nonzero audio over this sequence. No external SFX is used.

The walk command/thread pattern is measured in original EVE 22010700. The
opponent sound and five-frame mode-33 white fades match original EVE 22080100
(sound-bank load row 853, effect row 899, appearance rows 903-907).

`tests/staging_replay.jsonl` reproduces the new-game gathering. The longer
`tests/exploration_replay.jsonl` now allows time for the formation before dialogue.
All 42 tests pass, as do independent archive/text validation, exact manifest,
byte reversal and xdelta round trip. ROM assets, screenshots, audio and states
are private generated artifacts and remain ignored by Git.

The previously documented post-match return blocker remains unresolved.
Standalone melonDS, a complete result/replay cycle and save/reload are not
accepted by these staging checks. The older build evidence follows for context.

## Previous exploration and Paradoxe FC candidate

ROM: `build/inazuma_mystery.nds`.
SHA-256: `3e23f678ccbafeb9ff59ac553995b5a22f188ced3db993b9cd11892209d89367`.
Core: melonDS Libretro 0.9.3 `4081e83`, software rendering and generated FreeBIOS.
Standalone melonDS 1.1 is a separate, unverified target.

Observed on this exact final ROM from a fresh boot:

- Native Club de foot scenery, free movement and the entrance sparkle interaction.
- All 44 opening lines and seven surprise-opponent exchanges reach match setup.
- All four opponent actors and portraits appear during the reveal, including
  Canon Evans (`build/aftermath-final/line-47.png`).
- Native match setup displays Paradoxe FC and the recognizable opponent sprites
  (`build/aftermath-final/setup.png`).

A shortened-opening diagnostic ROM uses the same opponent template and return
logic. Its read-only match RAM confirms Nero 2141, Joseph King 21, young Seymour
Hillman 2221 and Canon Evans 2470, all at level 1. Gameplay reaches full time.
The scoped result helper records defeat 3, preserves tutorial bits (10022=E39),
clears return registration 1001A and enters the native return. **The lower screen
then remains black; neither the authored conversation nor free movement resumes.**
Diagnostic evidence: `build/aftermath-probe/end-4.png`, `end-memory.bin`.
Do not treat the authored victory/defeat/replay paths as accepted gameplay.

The final cold-boot input sequence is `tests/exploration_replay.jsonl`.
Screenshots and states are private generated artifacts and are ignored by Git.
The final ROM passed exact-manifest, byte reversal and xdelta round-trip checks.
All 39 tests pass, covering item gates, named opponent identities and preserved
native match-return helpers. Independent validation checks 24 story entries,
the scoped MCH/MCHT pair, string bindings and unchanged unrelated resources.
Static checks do not establish runtime acceptance; `gameplay_tested` stays false.

Remaining work: fix native end-to-world handoff, exercise both result branches,
replay, save/reload and the standalone executable. Existing campaign saves and
states from earlier ROM builds are unsupported.

## Historical illustrated build (DeSmuME)

The following evidence belongs to the older illustrated ROM and its exact hash;
it does not describe the current exploration build.

Historical ROM: `build/inazuma_mystery.nds`.
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
