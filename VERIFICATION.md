# Verification index

Current runtime evidence and limitations: [RUNTIME_VERIFICATION.md](RUNTIME_VERIFICATION.md).

Machine-readable structural reports are `build/verification.json` and
`build/scene_semantics.json`. Source-only tests are run with
`python -m unittest discover -s tests -v` (29 passing tests).

REA installation verification is separate: `local/rea-setup/verification.json`
records configuration preservation, a successful MCP initialization and a
255-tool catalog response from REA 6.9.0. Its user configuration backup is
`C:\Users\louis\.codex\config.toml.rea.backup`. No optional native provider is installed.
