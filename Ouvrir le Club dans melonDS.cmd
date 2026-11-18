@echo off
setlocal
cd /d "%~dp0"
set "EMU=%~dp0local\tools\melonds\melonDS.exe"
if not exist "%EMU%" (
  echo melonDS.exe est absent. Lancez python src/setup_tools.py --only melonds.
  pause
  exit /b 1
)
echo Ouverture du club et de ses deux matchs amicaux dans melonDS.exe.
python -c "import sys;sys.path.insert(0,'src');from prepare_arena import ensure_built;ensure_built('club_native')"
if errorlevel 1 (
  pause
  exit /b 1
)
start "" /D "%~dp0build\club_native" "%EMU%" "%~dp0build\club_native\arena.nds"
