# Inazuma Eleven 2: Le Defi Mystere

## InazumIA — salon de rencontres dynamiques

Lancer **`Lancer InazumIA.cmd`**, puis demander « Fais s'affronter Occulte et Zeus ».
Le chat prépare les équipes et six répliques entre leurs capitaines. Le dialogue
est affiché dans le jeu ; la rencontre peut être jouée manuellement ou confiée
à l'agent hybride. Le bouton de reprise arrête l'agent et laisse le jeu en pause.

Le catalogue validé de cette livraison contient **Occulte et Zeus**, dans les
deux sens. Le joueur hybride est expérimental ; sa délégation peut être arrêtée
à tout moment et ne garantit pas une victoire.

La ROM d'arène est construite une seule fois depuis votre original. Les affiches
suivantes se préparent en RAM, dans la même session. « Nouvelle rencontre »
restaure le checkpoint initial de cette session sans recharger la ROM.

Les agents utilisent LM Studio en local ou le CLI Codex selon le moteur choisi.
Le joueur lit les positions et la possession en mémoire, gère les menus connus
par règles, puis utilise le texte pour les choix reconnus et l'image en secours.
La préparation manuelle reste disponible sans agent. Le serveur et les scripts
de construction utilisent Python 3.11+ ; l'adaptateur MCP a son environnement
séparé. Voir [DELIVERY.md](DELIVERY.md) et [WEB_AND_MCP.md](WEB_AND_MCP.md).

Le texte ci-dessous documente également le scénario historique « Défi Mystère »,
conservé comme profil séparé. Ses anciennes captures ne prouvent pas le parcours
de l'arène ; les vérifications de livraison sont consignées séparément.

A local modification of the user-supplied French Tempete de Glace Nintendo DS
ROM. New Game now starts in the real, sunny Raimon **Club de foot** map,
with free movement. Walk north towards the clubhouse and examine the sparkling
object just to the left of its entrance with **A**. Only that interaction starts
the 44-line French opening, seven surprise-opponent introductions, and the
native football challenge against **Paradoxe FC**: Nero, Joseph King, young
Seymour Hillman and Canon Evans.

The five-player squad is Mark, Jack, Daniel Hatch, Byron Love and Nathan from
the Empereurs noirs, initialized at level 1. The conversation gathers their
native actors in the 3D clubhouse scenery; it no longer covers the map with
fullscreen illustrations. The upper screen retains the native area map.
The entrance interaction uses a native fade and staggered walking arrivals for
Raimon. The Paradoxe FC reveal uses the original 2D_170/770 sound and mode-33
white flash, with the opponents created while the lower screen is white.

Victory/defeat conversations and a short replay exchange are authored and wired
into the scene. **Their automatic runtime entry is still blocked after the
match**: the diagnostic native return currently leaves the lower screen black.
This build is not accepted as a complete playable episode.

**Run:** double-click `Jouer au Defi Mystere.cmd`, choose **Nouvelle partie**,
enter a save-file name and confirm **OK**. Use a fresh game. Skip the original
opening movie with A or Start, then advance the original introduction notices.
See [RUN_SCENARIO.md](RUN_SCENARIO.md) for controls and
[RUNTIME_VERIFICATION.md](RUNTIME_VERIFICATION.md) for observed runtime evidence.

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

The first chapter retains its native new-game/map/portal initialization and
event-return queue. Campaign event requests are neutralized at their callers;
the queue itself is no longer redirected. `scene_exploration.py` changes the
initial map to `mr07b05`, places a native 2004/group-28 sparkle at the entrance,
and gates callback 0x1014 on map, actor ID and actor group. Arrival callback
0x1017 places the object and initial player position without launching dialogue.
The object queues entry 22010100, whose 0x1023 callback stages the conversation
and launches native match 35 from original event 22010700. Other chapter
dispatchers remain isolated; existing campaign saves are unsupported.

Twenty-four selected compressed entries use space reclaimed from replaced
chapter scripts. Selected PKH offsets/sizes may change; unrelated entries,
ROM size and NitroFS allocation remain unchanged. Archive ownership, bounds
and non-overlap are independently checked. Both initial-team templates and the
first chapter's explicit roster initialization use the five requested players.
`scene_opponents.py` changes only team 70, used exclusively by match 35.
The native MCH/MCHT archives are now preserved byte for byte. The earlier
experimental result bypass has been removed. Regular-challenge mode returns to
the chapter restoration callback, which captures the outcome before continuation. The authored aftermath uses persistent outcome
flags and a chapter map-arrival queue. Runtime return remains blocked; see the
current evidence and limitations in `RUNTIME_VERIFICATION.md`.

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

The earlier illustrated build had a reported black screen after the new-game
notices in standalone melonDS 1.1. The current exploration build changes the
new-game map path and has runtime checks in the Libretro port. These checks
do not establish acceptance in the standalone executable.
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
