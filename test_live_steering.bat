@echo off
title ATS Hand Steering - Live Diagnostic Test
cd /d "%~dp0"
echo ========================================================
echo   ATS Visual Hand Steering - Live Axis Diagnostic
echo ========================================================
echo.
python\python.exe test_live_steering.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Trying system python...
    python test_live_steering.py
)
pause

