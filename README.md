# InazumIA

**Compose une affiche, fais parler les capitaines et joue le match dans le moteur Nintendo DS.**

InazumIA est un projet de fans autour d’*Inazuma Eleven 2 : Tempête de Glace*. Son salon web affiche les deux écrans de la DS et permet de préparer un match, de le jouer au clavier ou au tactile, puis de revenir au salon pour enchaîner.

[Prise en main](#prise-en-main) · [Architecture](#architecture) · [Documentation](#documentation)

## Du vestiaire au terrain

> Fais s’affronter Occulte et Zeus.

- **Prépare la rencontre.** Choisis les équipes ou donne une consigne au coach. L’organisateur peut écrire six répliques de capitaines qui s’affichent dans le jeu avant le coup d’envoi. La préparation manuelle utilise un dialogue prédéfini.
- **Joue ou délègue.** Prends les commandes au clavier ou au tactile. Essaie le pilote déterministe ou le pilote IA, puis reprends la main à tout moment. Les pilotes sont expérimentaux et peuvent s’arrêter avant la fin du match.
- **Écoute le match.** Active le commentaire vocal ou garde les sous-titres. Chester et Neuille annoncent les actions reconnues et font le bilan à la mi-temps et au coup de sifflet final.
- **Recrute avec Celia.** Propose un joueur dans le panneau de recrutement. Après confirmation, il peut rejoindre l’équipe au prochain match préparé en arène.
- **Enchaîne les affiches.** Le bouton **Nouvelle rencontre** restaure le checkpoint initial. Les équipes et le dialogue suivants sont préparés en mémoire. Un changement de recrutement peut nécessiter une ROM de session actualisée.
- **Passe voir Hillman.** Dans le navigateur, **Entrer dans le local** te laisse rejoindre Hillman. Parle-lui pour ouvrir sa route native et ses deux matchs amicaux. [Matchs amicaux du club](docs/guides/CLUB_FRIENDLIES.md)

## Prise en main

Il te faut **Windows**, **Python 3.11+**, ta ROM française de *Tempête de Glace* (**BEBF, révision 0**) et le cœur **melonDS Libretro** validé par le projet. Les empreintes SHA-256 des deux fichiers figurent dans les [prérequis de livraison](docs/guides/DELIVERY.md#prérequis).

```powershell
git clone https://github.com/hemvall/REA-Inazuma.git
cd REA-Inazuma
```

1. Place ta ROM dans `rom/original.nds` et le cœur validé dans `local/tools/melonds-core/melonds_libretro.dll`.
2. Installe les dépendances ROM avec `python -m pip install -r requirements-rom.txt`, puis ouvre **Lancer InazumIA.cmd**. Le lanceur prépare l’arène et ouvre le salon sur `http://127.0.0.1:18765`.
3. Sélectionne **Occulte** et **Zeus**, clique sur **Préparer le match**, puis sur **Lancer le dialogue**.

Le parcours manuel et le pilote déterministe fonctionnent sans modèle. Le coach, le pilote IA et les réactions générées de Chester utilisent le moteur local. Le client MCP est facultatif. [Configurer LM Studio ou MCP](docs/guides/WEB_AND_MCP.md)

## Architecture

| Composant | Rôle |
| --- | --- |
| [Salon web](web/) | Sélection des équipes, affichage des deux écrans et commandes DS. |
| [Session et émulation](src/game_session.py) | Worker isolé, entrées DS, captures et checkpoints. |
| [Service d’arène](src/arena_service.py) | Préparation des rencontres en mémoire, dialogue des capitaines et délégation du jeu. |
| [Commentaire](src/chester.py) | Événements confirmés et bilans de match. Le navigateur gère les sous-titres et la voix. |
| [Recrutement](src/recruitment.py) | Résolution des demandes de Celia et préparation des recrues. |
| [Serveur MCP](src/mcp_server.py) | Accès à la même session depuis un client compatible. |

Le pilote s’appuie sur l’état du match lu en mémoire et sur la reconnaissance des menus. Le worker traduit les actions reconnues en entrées DS. Le lanceur construit l’arène à partir de la ROM originale lors de la préparation initiale.

## Documentation

- [Salon web et MCP](docs/guides/WEB_AND_MCP.md) — commandes, configuration des modèles et protocole.
- [Livraison](docs/guides/DELIVERY.md) — versions attendues, empreintes et construction.
- [Vérifications](docs/verification/VERIFICATION.md) — procédures, résultats de l’audit et preuves historiques.
- [Défi Mystère](docs/guides/RUN_SCENARIO.md) — scénario historique jouable jusqu’au match. Le retour automatique après le match reste bloqué. [Vérification du scénario](docs/verification/RUNTIME_VERIFICATION.md)
- [Architecture et implémentation](docs/architecture/) — conception, scène autonome et initialisation des équipes.
- [Plans et suivi](docs/plans/) — historique de développement, MCP et commentateur Chester.

Les ROM, sauvegardes, ressources extraites et binaires d’émulation restent locaux. InazumIA est un projet non officiel.

<details>
<summary>Notes techniques du profil historique Défi Mystère</summary>

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

**Run:** open `build/inazuma_mystery.nds` in portable melonDS and choose
**Nouvelle partie**. See the [scenario guide](docs/guides/RUN_SCENARIO.md) for
the build and controls. The Club launcher opens the separate Club profile.

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
- `docs/architecture/TEAM_INITIALIZATION.md`: native roster/level evidence and memory layout.
- `Ouvrir le Club dans melonDS.cmd`: portable melonDS launcher for the Club profile.

ROMs, extracted resources, private manifests, emulator states and downloaded
tools are ignored by Git. Do not commit or redistribute copyrighted ROM assets.
The earlier `inazuma_scene_experimental.nds` is a historical candidate.

## Build

See the [scenario build guide](docs/guides/RUN_SCENARIO.md#rebuild) for the
xdelta3 setup and build commands, and the
[verification index](docs/verification/VERIFICATION.md) for the test suite.

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
current evidence and limitations in `docs/verification/RUNTIME_VERIFICATION.md`.

`src/emulator_probe.py` is a small libretro test host. It executes the actual ROM,
feeds emulated DS input and writes framebuffer PNGs, without controlling Windows
apps. It needs the separately downloaded melonDS libretro DLL. The input
sequence `tests/exploration_replay.jsonl` targets the exploration build.
`tests/scenario_replay.jsonl` records the earlier illustrated route. The
sequences contain controller input.

The Club launcher uses portable melonDS. The automated probe uses the
[verified melonDS Libretro core](docs/guides/DELIVERY.md#prérequis)
(version 0.9.3 4081e83). Install portable melonDS with:

```powershell
python src/setup_tools.py --only melonds
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

</details>
