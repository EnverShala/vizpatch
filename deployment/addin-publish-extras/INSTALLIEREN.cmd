@echo off
REM Doppelklick genuegt: entfernt Download-Sperre, installiert Zertifikat, startet Setup.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0vertrauen-einrichten.ps1"
if errorlevel 1 (
  echo.
  echo FEHLER beim Einrichten des Zertifikats - Setup wird NICHT gestartet.
  pause
  exit /b 1
)
echo.
echo Starte Setup...
start "" "%~dp0setup.exe"
