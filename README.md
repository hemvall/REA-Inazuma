# Inazuma Eleven 2: Le Defi Mystere

A local modification of the user-supplied French Tempete de Glace Nintendo DS
ROM. The current build contains a four-part, 44-line opening story targeting
five minutes of reading/staging, native illustrated backgrounds and an existing
football match. The five-player team is Mark, Jack, Daniel Hatch, Byron Love and
Nathan from the Empereurs noirs, initialized at level 1.

**Run:** double-click `Jouer au Defi Mystere.cmd`, choose **Nouvelle partie**,
enter a save-file name and confirm **OK**. See [RUN_SCENARIO.md](RUN_SCENARIO.md).
The launcher needs no Codex desktop-control permission.

The scene uses existing club-sign, notebook and football illustrations behind
the message window. The lower screen carries the scene; the upper screen remains
black during these illustrated sequences. The unresolved native 3D map renderer
is no longer used as the visible scene background. Full result/replay and save
acceptance remain separate runtime checks.
At power-on the original `op00` opening movie still plays. Press **A** or
**Start** to skip to the title menu, then choose **Nouvelle partie** to enter the
episode. See [RUNTIME_VERIFICATION.md](RUNTIME_VERIFICATION.md)
for evidence and the exact tested build, rather than treating static checks as
gameplay acceptance.

## Input and output

Place your legally obtained original at `rom/original.nds`.
Supported original: **BEBF revision 0**, SHA-256
`1e67c699a6b3ecfb5230e8c2245746879fab57123277651da74b4cc9b8ba25d3`.
The Downloads source remains unchanged.

- `build/inazuma_mystery.nds`: current scenario ROM.
- `dist/inazuma_mystery.xdelta`: patch for that exact original.
- `build/verification.json`: hashes, exact-manifest/reversal and xdelta checks.
- `build/scene_semantics.json`: callback, resource and text-binding checks.
- `story/standalone_scene.json`: authored French text and measured character IDs.
- `story/five_minute_scenario.md`: readable French script with stage directions.
- `TEAM_INITIALIZATION.md`: native roster/level evidence and memory layout.
- `Jouer au Defi Mystere.cmd`: portable melonDS launcher.

ROMs, extracted resources, private manifests, emulator states and downloaded
tools are ignored by Git. Do not commit or redistribute copyrighted ROM assets.
The earlier `inazuma_scene_experimental.nds` is a historical candidate.

## Build

Python 3.11+ works; Python 3.12+ is recommended. No Python dependencies are needed
for building or validating. xdelta3 is needed to produce the patch. Portable
official tools are downloaded by `python src/setup_tools.py`; the build finds
the downloaded xdelta3 without changing PATH.

```powershell
python src/inspect_rom.py
python src/prepare_scene.py
python src/build.py --manifest local/scene_patch.json
python src/validate_scene.py
python -m unittest discover -s tests -v
```

Build refuses the wrong original hash, checks original resource bytes, applies
resource edits without moving NitroFS files, checks reversal byte for byte,
then verifies an xdelta encode/decode round trip before publishing outputs.
The source ROM is never overwritten.

To install the patch using your exact supported original:

```powershell
xdelta3 -d -s rom/original.nds dist/inazuma_mystery.xdelta build/installed.nds
```

Compare its SHA-256 with `modified_sha256` in `build/verification.json`.

## Implementation

`src/nds.py` validates the NDS header CRC and bounded NitroFS layout.
`ie2_formats.py` handles the measured PackNum type-0 index, LZ10 compression and
length-prefixed EVET records. `ssd.py` reads/emits the observed SSD instruction
layout and checks one-based references, paired blocks and SST bindings.
`prepare_scene.py` verifies unit names against the actual ROM and emits the new
callbacks while retaining required common helper code from the original.

The first chapter retains its native initialization and redirects its event-queue
helper into the new scene. The other ten chapter dispatchers are replaced to
disconnect original campaign triggers. The opening uses entry key 22010100 and map
`mr02b03`, and uses native match 35 from original event 22010700. Shared resources,
native executable code, original football data and unrelated event entries remain
present. Their physical deletion would risk shared dependencies.

Twenty-four selected compressed entries use space reclaimed from replaced
chapter scripts. Selected PKH offsets/sizes may change; unrelated entries,
ROM size and NitroFS allocation remain unchanged. Archive ownership, bounds
and non-overlap are independently checked. Both initial-team templates and the
first chapter's explicit roster initialization use the five requested players.
Native football scripts are unchanged; result/replay remains experimental.
The current post-match handler branches on the match result inside one callback;
it does not rely on the pre-match event counter surviving native return.

`src/emulator_probe.py` is a small libretro test host. It executes the actual ROM,
feeds emulated DS input and writes framebuffer PNGs, without controlling Windows
apps. It needs the separately downloaded melonDS libretro DLL. The input
sequence is `tests/scenario_replay.jsonl`; this is a regression aid, not a bundled
save state or a substitute for the ROM.

The launcher now uses standalone melonDS (tested binary: 1.1). The automated
probe uses the separate Libretro melonDS port (tested: 0.9.3 4081e83), not the
same executable or core version. Install either with:

```powershell
python src/setup_tools.py --only melonds
python src/setup_tools.py --only melonds-core
```

Standalone settings stay in `local/tools/melonds/portable/`. The probe uses DS
direct boot, French, software rendering and vertically stacked screens without
a gap. Touch input uses lower-screen pixels `x=0..255, y=0..191`. The old
DeSmuME-specific `--frame-skip` option is removed. Save states are not shared
between the standalone emulator, Libretro port or DeSmuME.

This migration does not change the ROM, menu, movies or scenario scripts. A
black screen after the new-game notices was reported in standalone melonDS 1.1
and remains unresolved. Libretro checks do not establish standalone acceptance.
Downloaded archive hashes are recorded in `local/tools/downloads.json`; keep
the nightly Libretro archive to reproduce the exact tested binary. No Nintendo
BIOS or firmware is downloaded.

Older `prepare_proof.py`, `patch_dialogues.py` and `validate_proof.py` retain the
one-line proof workflow. Running the proof build against the default output would
replace the current scenario build; use the scene commands above for this project.

## Research references

- [Tinke](https://github.com/pleonex/tinke) and its PackNum reader.
- [SceneScriptData](https://github.com/Tiniifan/SceneScriptData): SSD/SST format
  research; independent parsing was also used during investigation.
- [libretro C ABI](https://github.com/libretro/libretro-common/blob/master/include/libretro.h)
  and [melonDS core](https://github.com/libretro/melonDS).
- [Dialogue research](https://gbatemp.net/threads/inazuma-text-editor.604619/):
  `evet.pkb` is relevant, but index 1174 was not assumed for this ROM.

REA 6.9.0 was separately installed for Codex with the user's approval. Its MCP
handshake exposed 255 tools; the current chat needs a client reload to discover
them. No optional native-analysis engine was installed. REA is not a dependency
of these build scripts.
