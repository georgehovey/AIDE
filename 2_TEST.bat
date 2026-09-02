@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title AIDE - Free test run
where py >nul 2>&1
if %errorlevel%==0 (set PY=py) else (set PY=python)

echo ============================================
echo   AIDE test run - FAKE data, costs nothing
echo   This only checks that everything works.
echo ============================================
echo.

if exist results rmdir /s /q results
cd runner
%PY% run.py --corpus ..\corpus --out ..\results --n 3 --mock
if errorlevel 1 goto oops
echo.
echo --- analysis ---
echo.
%PY% analyze.py --corpus ..\corpus --results ..\results
if errorlevel 1 goto oops
cd ..
rmdir /s /q results
echo.
echo ============================================
echo   It works. The numbers above are FAKE.
echo   Next: double-click 3_PILOT.bat
echo ============================================
pause
exit /b 0

:oops
cd ..
echo.
echo Something went wrong. Copy everything above and send it to Claude.
pause
