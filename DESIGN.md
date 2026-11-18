# InazumIA — Pixel match lobby

The lobby is a game menu for choosing a fixture, preparing its captain dialogue,
and playing the existing Nintendo DS simulation. The primary action is preparing
the selected fixture; the live screens and match controls become central afterward.

Use an adventurous DS-era football RPG direction: midnight navy, electric blue,
warm yellow highlights, stepped corners, hard offset shadows and pixel emblems.
Press Start 2P is reserved for short headings and numbers; readable system type
carries instructions and dialogue. All assets are local. The stadium background
is generated artwork, not an observation of the running emulator.

Desktop composition: compact masthead, fixture selection, then a narrow match
setup column, a dominant stadium/game screen and a compact coach/control column.
On tablets the coach column moves below the arena. On phones everything stacks,
with the fixture and preparation ahead of the live screen. Preserve the stacked
256×384 screen image and its lower-screen touch-coordinate mapping.

Required states: no session, preparing, ready, human control, agent control,
paused, final result, disconnected and error. Only show real scores if supplied
by the emulator; no invented progress, match clock or statistics. Keep manual
preparation, chat, both agent backends and external MCP control accessible.

Finish: inspect desktop and mobile screenshots; exercise fixture swapping,
preparation, live controls, engine selection and failures with an isolated API
fixture. Check overflow, focus, reduced motion and all existing DOM hooks.
