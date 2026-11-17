@echo off
setlocal
set "EMU=%~dp0local\tools\melonds\melonDS.exe"
set "ROM=%~dp0build\inazuma_mystery.nds"
if not exist "%EMU%" (
  echo melonDS is missing. Run python src/setup_tools.py --only melonds from the project folder.
  pause
  exit /b 1
)
if not exist "%ROM%" (
  echo The scenario ROM is missing. See RUN_SCENARIO.md for build instructions.
  pause
  exit /b 1
)
start "" /D "%~dp0build" "%EMU%" "%ROM%"
exit /b 0
