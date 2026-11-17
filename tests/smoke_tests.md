# Gameplay acceptance procedure

Current standalone scenario: see `../RUNTIME_VERIFICATION.md` for observed
cold-boot dialogue and football checks, exact hash and remaining failures.
Use `scenario_replay.jsonl` for the current new-game input sequence. Complete
victory, defeat, replay and save/reload acceptance remains outstanding.

## Historical one-line proof checklist

The remaining procedure describes the earlier proof, not the current scenario.
Status: NOT RUN. Do not mark any item passed from a structural check alone.

Current proof target: supplied BEBF revision 0, opening wake-up conversation in
Mark's home, new game. After the naming/opening sequence, advance until Mark
reacts to the start of training: text ID 13 should read `Raimon, a nous le defi!`.
The route and speaker are inferred from resources, not observed on screen.
Desktop automation was denied access to DeSmuME; run these checks manually.

Record original/patched SHA-256, game code, revision, edition, ROM language,
emulator version/settings and save SHA-256. Back up saves; use separate original
and patched save copies. Never overwrite the only campaign save.

1. Boot the original ROM in DeSmuME using the intended French language setting.
   Record the exact new-game route or save position and inputs to the chosen
   scene, plus the original speaker and line in local private notes.
2. Boot the patched ROM with the equivalent copied save. Confirm title/start
   screens work and reach the same scene through the recorded inputs.
3. Confirm the original French proof line appears in the intended character's
   dialogue box. Capture both screens. Check accents, wrapping, portrait,
   punctuation and complete line display. Advance the dialogue normally.
4. Confirm transitions and player control return. Move, open menus, leave and
   re-enter the area. Ensure the event does not repeat or block progression.
5. Save through the normal game menu. Close the emulator, restart and load the
   battery save (not merely a save state). Confirm position and progression.
6. Only after 1–5 pass, expand the selected contiguous scene using observed
   speakers and slots, then repeat all checks with the expanded build.
7. If a match is included, confirm the original opponent, start transition and
   normal football controls. Test victory and defeat on separate copied saves;
   check original retry/branch behavior and normal control after completion.
8. If post-match dialogue is edited, verify each speaker and line, area return,
   saving/reloading and the next original progression event independently.

For each step, record PASS/FAIL/NOT RUN, build hash, route, evidence and issues.
Record precise menu names and inputs from the manual run to replace the
resource-derived route above with an observed route.
