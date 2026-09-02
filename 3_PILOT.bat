@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title AIDE - Real pilot run
where py >nul 2>&1
if %errorlevel%==0 (set PY=py) else (set PY=python)

REM ---- Verify these slugs at https://openrouter.ai/models before running ----
set PRINCIPAL=anthropic/claude-haiku-4.5
set AIDS=anthropic/claude-opus-4.1 deepseek/deepseek-chat
set WORKERS=4
REM --------------------------------------------------------------------------

if "%AIDS%"=="" goto badconfig
if "%PRINCIPAL%"=="" goto badconfig

echo ============================================
echo   AIDE pilot - REAL run, costs real money
echo ============================================
echo.
echo Principal model: %PRINCIPAL%
echo Aid models:      %AIDS%
echo Parallel calls:  %WORKERS%
echo.

if exist results (
  echo An earlier run left results in place.
  echo.
  echo   Press ENTER to CONTINUE it - finished work is kept, failures are retried.
  echo   Type  FRESH  and press Enter to delete everything and start over.
  echo.
  set /p CHOICE=Choice:
  if /i "%CHOICE%"=="FRESH" rmdir /s /q results
  echo.
)

echo Paste your OpenRouter API key and press Enter.
echo (Get one at https://openrouter.ai/keys - starts with sk-or-)
echo.
set /p OPENROUTER_API_KEY=Key:
echo.

cd runner
echo Running: run.py --n 5 --provider openrouter --principal %PRINCIPAL% --aid-models %AIDS% --workers %WORKERS%
echo.
%PY% run.py --corpus ..\corpus --out ..\results --n 5 --provider openrouter --principal %PRINCIPAL% --aid-models %AIDS% --workers %WORKERS%
if errorlevel 1 goto oops
echo.
echo ================ ANALYSIS ================
echo.
%PY% analyze.py --corpus ..\corpus --results ..\results > ..\ANALYSIS_OUTPUT.txt
type ..\ANALYSIS_OUTPUT.txt
cd ..
echo.
echo ============================================
echo   Done. Send Claude the file ANALYSIS_OUTPUT.txt
echo ============================================
pause
exit /b 0

:badconfig
echo.
echo CONFIG ERROR: the PRINCIPAL or AIDS line near the top of this file is empty.
echo Right-click this file, choose Edit, and check the lines beginning  set AIDS=
pause
exit /b 1

:oops
cd ..
echo.
echo Something went wrong. Copy everything above and send it to Claude.
echo Nothing is lost - run this file again and press ENTER to continue.
pause
