# Run Le Defi Mystere locally

Double-click `Jouer au Defi Mystere.cmd` in the project folder. It opens the
scenario ROM directly in the downloaded portable DeSmuME. It does not require
Codex Computer Use permissions, change file associations, or install software.

The original `op00` opening movie plays at power-on. Press **A** or **Start** to
skip it, then select **Nouvelle partie**. The new episode begins after the
save-name entry and the original legal/story introduction.

At the game title choose **Nouvelle partie**, enter a save-file name and confirm
with **OK**. Advance the two legal notices and story introduction with the
Nintendo DS **A** button. The authored scene then starts. Use the emulator's
touchscreen with the mouse for football controls. Use a fresh game, not an old
campaign save state.

The ROM to open manually is `build/inazuma_mystery.nds`.
The patch for the exact supported original is `dist/inazuma_mystery.xdelta`.
The older `inazuma_scene_experimental.nds` is an earlier candidate, not this build.

## Current episode

The new story has 44 opening lines in four illustrated sequences, approximately
five minutes excluding football and depending on reading speed. Mark, Jack,
Daniel Hatch, Byron Love and Nathan Empereur Noir form the level-one team.
The scene uses native illustrations on the lower screen; the upper screen is
black during the illustrated dialogue. The reused native football
event is a four-a-side, first-goal challenge, with the fifth squad member available
in the roster. Full result/replay and save acceptance remain experimental.
The normal title screen remains; automatic power-on entry is not implemented.
See `RUNTIME_VERIFICATION.md` for exact tested builds and remaining checks.

## Rebuild

```powershell
python src/prepare_scene.py
python src/build.py --manifest local/scene_patch.json
python src/validate_scene.py
python -m unittest discover -s tests -v
```

The original `src/prepare_proof.py` command generates the old one-dialogue proof.
Use `prepare_scene.py` for the standalone scenario.
