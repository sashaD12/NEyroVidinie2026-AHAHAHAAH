@echo off
setlocal
cd /d "%~dp0"
if not exist bin\ad_enhance.exe (
  call build.bat
  if errorlevel 1 exit /b 1
)
if "%AD_PORT%"=="" set AD_PORT=8766
echo Open http://127.0.0.1:%AD_PORT%
python web\server.py
