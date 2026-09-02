@echo off
title AIDE - Setup
echo ============================================
echo   AIDE Setup - installs what Python needs
echo ============================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (set PY=py) else (
  where python >nul 2>&1
  if %errorlevel%==0 (set PY=python) else (
    echo Python is not installed.
    echo.
    echo Go to https://www.python.org/downloads/
    echo Download the latest Windows installer and run it.
    echo IMPORTANT: tick the box "Add python.exe to PATH" on the first screen.
    echo Then run this file again.
    echo.
    pause
    exit /b 1
  )
)

echo Found Python:
%PY% --version
echo.
echo Installing the two libraries this needs...
echo.
%PY% -m pip install --upgrade pip
%PY% -m pip install -r runner\requirements.txt
echo.
echo ============================================
echo   Setup done. Next: double-click 2_TEST.bat
echo ============================================
pause
