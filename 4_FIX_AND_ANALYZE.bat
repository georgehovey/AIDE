@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title AIDE - Repair and re-analyze
where py >nul 2>&1
if %errorlevel%==0 (set PY=py) else (set PY=python)

echo ============================================
echo   Repairing result filenames, then analyzing
echo   your EXISTING data. No API calls, no cost.
echo ============================================
echo.
cd runner
%PY% migrate.py ..\results
if errorlevel 1 goto oops
echo.
%PY% analyze.py --corpus ..\corpus --results ..\results > ..\ANALYSIS_OUTPUT.txt
type ..\ANALYSIS_OUTPUT.txt
cd ..
echo.
echo ============================================
echo   Send Claude the file ANALYSIS_OUTPUT.txt
echo ============================================
pause
exit /b 0

:oops
cd ..
echo Something went wrong. Copy the text above and send it to Claude.
pause
