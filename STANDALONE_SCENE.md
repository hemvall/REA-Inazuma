# Standalone scene implementation

The current runnable candidate is `build/inazuma_mystery.nds`, launched with
`Jouer au Defi Mystere.cmd`. See README, RUN_SCENARIO and RUNTIME_VERIFICATION.

The game retains its native title and new-game naming flow. Its chapter dispatch
routes into the authored event at key 22010100, instead of the original campaign.
The event creates Mark, Jack, Daniel Hatch, Byron Love and Nathan from the
Empereurs noirs. It presents 44 authored French lines in four illustrated
sequences, then starts original native football match 35.

Native character IDs are resolved through unitno.dat and named 96-byte
unitbase.dat records: Mark 1, Jack 3, Hatch 29, Byron 190 and Dark Nathan 2430.
Record indices differ from native IDs; both mappings are checked. Positions reuse coordinates from
the original riverside setup. Common camera and lifecycle helpers are extracted
from the exact original ROM. New bytecode is emitted deterministically in Python.

The first chapter preserves its original initialization and redirects the
event-queue helper to the new event. The other ten chapter dispatchers use the
isolated scene dispatcher. Cold-boot testing reaches the native legal notices,
then the authored dialogue and native match. The native map renderer remains
unresolved. Existing club-sign, notebook and football illustrations provide
visible backgrounds behind the message window at measured priority 25000.
The upper screen is black during the lower-screen illustrated scenes.

An older build froze after the match. The current source uses one unconditional
match-return callback with result branches, rather than two callbacks requiring
the pre-match counter. Runtime acceptance for the current hash is recorded
separately in RUNTIME_VERIFICATION; source intent alone is not a passed check.

The first chapter's explicit twelve-player remove/recruit block is replaced by
five native additions at level 1. Both initial-team resource templates match the
requested roster. Read-only ARM9 memory checks confirm actual runtime state.

The ordinary campaign assets remain physically present but event dispatch is
redirected. Existing campaign saves and emulator states are unsupported. The
native title bypass and a new campaign save system are not implemented.

For reproduction use `prepare_scene.py`, `build.py --manifest local/scene_patch.json`
and `validate_scene.py`. The older experimental-named artifacts are historical.
