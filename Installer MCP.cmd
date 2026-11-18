@echo off
cd /d "%~dp0"
python -m venv local\agent-venv
if errorlevel 1 goto failed
local\agent-venv\Scripts\python.exe -m pip install -r requirements-agent.txt
if errorlevel 1 goto failed
echo MCP installe. Configuration dans WEB_AND_MCP.md.
pause
exit /b 0
:failed
echo Installation interrompue. Consultez l'erreur ci-dessus.
pause
exit /b 1
