@echo off
setlocal
cd /d "%~dp0"
title Blink tests (work package 2)
set "PY=%~dp0.venv\Scripts\python.exe"
set "LOG=%~dp0app_log.txt"

if not exist "%PY%" (
    echo Python environment not found: %PY%
    pause
    goto done
)

rem Direct choice: eye_tests.bat 3  (no menu)
if not "%~1"=="" (
    set "CHOICE_NO=%~1"
    goto run
)

:menu
cls
echo ==========================================================
echo   BLINK TESTS (WORK PACKAGE 2)
echo ==========================================================
echo.
echo   1  Label the test videos (5 videos, slow motion; labeled ones are skipped)
echo   2  Show label status
echo   3  Evaluate blink detection (target: 85 percent or more)
echo   4  Controlled long eye closure test (camera, privacy mode, 10 trials)
echo   5  Label ALL videos again from scratch (old labels are kept)
echo   6  Compare the two labeling rounds (how consistent are the labels?)
echo   Q  Quit
echo.
echo   Labeling: press B at every blink, press Q when done.
echo   Controlled test: close your eyes at the HIGH beep and keep them closed until the LOW beep.
echo   No image is saved.
echo.
choice /c 123456Q /n /m "Choice: "
if errorlevel 7 goto done
set "CHOICE_NO=%errorlevel%"

:run
set "COMMAND="
if "%CHOICE_NO%"=="1" set "COMMAND=tools\test_videos.py label"
if "%CHOICE_NO%"=="2" set "COMMAND=tools\test_videos.py status"
if "%CHOICE_NO%"=="3" set "COMMAND=tools\evaluate_blinks.py"
if "%CHOICE_NO%"=="4" set "COMMAND=tools\controlled_test.py"
if "%CHOICE_NO%"=="5" set "COMMAND=tools\test_videos.py label --fresh"
if "%CHOICE_NO%"=="6" set "COMMAND=tools\compare_labels.py"

if not defined COMMAND (
    echo Invalid choice: %CHOICE_NO%
    pause
    goto done
)
if defined EYE_DRY_RUN (
    echo [DRY RUN] python %COMMAND%
    goto done
)
"%PY%" %COMMAND% 2>>"%LOG%"
echo.
pause
if not "%~1"=="" goto done
goto menu

:done
endlocal
