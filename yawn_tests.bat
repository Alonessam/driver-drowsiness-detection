@echo off
setlocal
cd /d "%~dp0"
title Yawn tests (work package 3)
set "PY=%~dp0.venv\Scripts\python.exe"
set "LOG=%~dp0app_log.txt"

if not exist "%PY%" (
    echo Python environment not found: %PY%
    pause
    goto done
)

rem Direct choice: yawn_tests.bat 4  (no menu)
if not "%~1"=="" (
    set "CHOICE_NO=%~1"
    goto run
)

:menu
cls
echo ==========================================================
echo   YAWN TESTS (WORK PACKAGE 3)
echo ==========================================================
echo.
echo   1  Pick the 5 yawn test videos (fixed random rule, once)
echo   2  Label the yawn test videos (press B in the middle of each yawn)
echo   3  Show label status
echo   4  Evaluate: labeled yawns (target 85 percent) and talking videos
echo   5  Evaluate only the talking videos (false yawns, target at most 1 per video)
echo   Q  Quit
echo.
choice /c 12345Q /n /m "Choice: "
if errorlevel 6 goto done
set "CHOICE_NO=%errorlevel%"

:run
set "COMMAND="
if "%CHOICE_NO%"=="1" set "COMMAND=tools\pick_test_videos.py"
if "%CHOICE_NO%"=="2" set "COMMAND=tools\test_videos.py label --kind yawn"
if "%CHOICE_NO%"=="3" set "COMMAND=tools\test_videos.py status --kind yawn"
if "%CHOICE_NO%"=="4" set "COMMAND=tools\evaluate_yawns.py"
if "%CHOICE_NO%"=="5" set "COMMAND=tools\evaluate_yawns.py --skip-labels"

if not defined COMMAND (
    echo Invalid choice: %CHOICE_NO%
    pause
    goto done
)
if defined YAWN_DRY_RUN (
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
