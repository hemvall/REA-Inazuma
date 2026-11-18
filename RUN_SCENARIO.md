# Run Le Defi Mystere locally

Double-click `Ouvrir le Club dans melonDS.cmd` in the project folder. It opens the
scenario ROM directly in the downloaded portable melonDS. It does not require
Codex Computer Use permissions, change file associations, or install software.

Install it with `python src/setup_tools.py --only melonds`. The launcher expects
`local/tools/melonds/melonDS.exe`; configuration lives in its `portable/` folder.
Configure DS buttons under **Config > Input and hotkeys** if no keys are mapped.
Use a new game and do not import DeSmuME save states.

For the separate automated Libretro port:

```powershell
python src/setup_tools.py --only melonds-core
python src/emulator_probe.py build/inazuma_mystery.nds --commands tests/scenario_replay.jsonl
```

Use `tests/exploration_replay.jsonl` for the current cold-boot exploration
route on the melonDS Libretro port. `scenario_replay.jsonl` is the historical
illustrated route. Standalone melonDS acceptance remains a separate check.

The original `op00` opening movie plays at power-on. Press **A** or **Start** to
skip it, then select **Nouvelle partie**. The new episode begins after the
save-name entry and the original legal/story introduction.

At the game title choose **Nouvelle partie**, enter a save-file name and confirm
with **OK**. Advance the two legal notices and story introduction with the
Nintendo DS **A** button. The authored scene then starts. Use the emulator's
touchscreen with the mouse for football controls. Use a fresh game, not an old
campaign save state.

The combined ROM opened by the launcher is `build/club_native/arena.nds`.
The patch for the exact supported original is `dist/inazuma_mystery.xdelta`.
The older `inazuma_scene_experimental.nds` is an earlier candidate, not this build.

## Current episode

After the original introduction you control Mark on the native **Club de foot**
map. Use the D-pad or the touchscreen to move. Walk north along the path towards
the clubhouse. Examine the sparkling object just to the left of the entrance
with **A** (the DS button, according to your emulator key mapping).

The story does not start just by arriving or pressing A away from the object.
After a brief native fade, Mark steps into place and Jack, Hatch, Byron and
Nathan walk in from the path. Wait until the group settles and dialogue begins.
The opponent reveal then uses the native sound and white flash.
The interaction gathers Mark, Jack, Hatch, Byron and Nathan in the actual 3D
scenery. Advance the 44 opening lines and seven Paradoxe FC introductions with A;
the native football challenge then follows. The reading target remains around five minutes, depending on pace.

The native challenge is a first-goal four-a-side event. All five requested
players are in the level-one squad. Full match result/replay and save/reload
acceptance remain experimental. The authored post-match conversations are
currently blocked by a black screen after native return; they are not accepted
as reachable gameplay. See `RUNTIME_VERIFICATION.md` for evidence.

## Rebuild

```powershell
python src/prepare_scene.py
python src/build.py --manifest local/scene_patch.json
python src/validate_scene.py
python -m unittest discover -s tests -v
```

The original `src/prepare_proof.py` command generates the old one-dialogue proof.
Use `prepare_scene.py` for the standalone scenario.
