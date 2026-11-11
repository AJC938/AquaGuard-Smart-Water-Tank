@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo AquaGuard environment is missing. Run the setup commands in README.md first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" desktop_launcher.py
if errorlevel 1 pause
