# Local lobby assets

- `stadium-pixel.png`: original AI-generated pixel-art stadium background created
  for the InazumIA lobby. It is decorative artwork, not an emulator screenshot.
- `PressStart2P-Regular.ttf`: Press Start 2P by CodeMan38, distributed under the
  SIL Open Font License. The complete license is in `OFL.txt`.
  Source: https://github.com/google/fonts/tree/main/ofl/pressstart2p
- `team-*.png`: official Raimon, Royal Academy, Occult and Zeus emblems from
  LEVEL-5's [Inazugle emblem catalog](https://zukan.inazuma.jp/en/item/emblem/).
- The ball, controller and lightning icons are inline SVG graphics in
  `web/index.html`, drawn on integer-coordinate grids.

The lobby loads these files locally and does not depend on a font or image CDN.
