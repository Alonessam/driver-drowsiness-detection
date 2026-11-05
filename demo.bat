@echo off
setlocal
cd /d "%~dp0"
title Driver Drowsiness Detection - Demo
set "PY=%~dp0.venv\Scripts\python.exe"
if not defined YAWDD_DIR set "YAWDD_DIR=%~dp0data\YawDD"
if not exist "%YAWDD_DIR%" if exist "%~dp0..\YawDD dataset" set "YAWDD_DIR=%~dp0..\YawDD dataset"
if not defined UTA_DIR set "UTA_DIR=%~dp0data\UTA-RLDD"
if not exist "%UTA_DIR%" if exist "%~dp0..\kaggle" set "UTA_DIR=%~dp0..\kaggle"
set "YAWDD=%YAWDD_DIR%\Mirror\Female_mirror"
set "LOG=%~dp0app_log.txt"

if not exist "%PY%" (
    echo Python environment not found: %PY%
    echo Follow the setup steps in README.md first.
    pause
    goto done
)

rem No argument: menu. If a video file is dropped onto this file, it is opened directly.
rem Argument 1-8: runs that menu option (example: demo.bat 3).
if "%~1"=="" goto menu
if exist "%~1" goto dropped
set "CHOICE_NO=%~1"
goto run

:dropped
set "VIDEO=%~1"
set "EXTRA="
goto open

:menu
cls
echo ==========================================================
echo   DRIVER DROWSINESS DETECTION - DEMO MENU
echo ==========================================================
echo.
echo   1  Camera
echo   2  Camera - privacy mode on (face not visible)
echo   3  YawDD yawning video - no glasses
echo   4  YawDD yawning video - glasses
echo   5  YawDD yawning video - sunglasses
echo   6  UTA-RLDD drowsy video (privacy mode on)
echo   7  Open measurement results page (349 videos, in the browser)
echo   8  PICK ANOTHER VIDEO (opens a file dialog)
echo   Q  Quit
echo.
echo   In the window:  g = toggle privacy mode    q = close
echo   Tip: you can drag a video file onto this file (demo.bat).
echo   Videos without sharing permission automatically open in privacy mode.
echo.
choice /c 12345678Q /n /m "Choice: "
if errorlevel 9 goto done
set "CHOICE_NO=%errorlevel%"

:run
set "VIDEO="
set "EXTRA="
if "%CHOICE_NO%"=="1" set "VIDEO=0"
if "%CHOICE_NO%"=="2" set "VIDEO=0"
if "%CHOICE_NO%"=="2" set "EXTRA=--privacy"
if "%CHOICE_NO%"=="3" set "VIDEO=%YAWDD%\1-FemaleNoGlasses-Yawning.avi"
if "%CHOICE_NO%"=="4" set "VIDEO=%YAWDD%\16-FemaleGlasses-Yawning.avi"
if "%CHOICE_NO%"=="5" set "VIDEO=%YAWDD%\17-FemaleSunGlasses-Yawning.avi"
if "%CHOICE_NO%"=="6" set "VIDEO=%UTA_DIR%\01\10.MOV"
if "%CHOICE_NO%"=="6" set "EXTRA=--privacy"
if "%CHOICE_NO%"=="7" goto results
if "%CHOICE_NO%"=="8" goto pick
if not defined VIDEO (
    echo Invalid choice: %CHOICE_NO%
    pause
    goto back
)

:open
if not "%VIDEO%"=="0" if not exist "%VIDEO%" (
    echo Video not found: %VIDEO%
    pause
    goto back
)
if defined DEMO_DRY_RUN (
    echo [DRY RUN] app.py --source "%VIDEO%" %EXTRA%
    goto back
)
echo Opening... (press q in the window to close)
"%PY%" app.py --source "%VIDEO%" %EXTRA% 2>>"%LOG%"
goto check

:pick
if defined DEMO_DRY_RUN (
    echo [DRY RUN] app.py --pick
    goto back
)
echo Opening file dialog...
"%PY%" app.py --pick 2>>"%LOG%"

:check
if errorlevel 1 (
    echo.
    echo An error occurred. Details: app_log.txt
    pause
)
goto back

:results
if not exist "%~dp0yawdd_detection_rate.csv" (
    echo Results file not found: yawdd_detection_rate.csv
    pause
    goto back
)
if defined DEMO_DRY_RUN (
    echo [DRY RUN] tools\results_page.py and start results.html
    goto back
)
"%PY%" tools\results_page.py >nul 2>>"%LOG%"
if errorlevel 1 (
    echo Could not build the results page. Details: app_log.txt
    pause
    goto back
)
start "" "%~dp0results.html"

:back
if not "%~1"=="" goto done
goto menu

:done
endlocal
