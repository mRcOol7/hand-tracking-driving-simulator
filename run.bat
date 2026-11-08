@echo off
title ATS Hand Steering Wheel
cd /d "%~dp0"

echo ========================================================
echo       ATS HAND-TRACKING VIRTUAL STEERING WHEEL
echo ========================================================
echo.

if exist "%~dp0python\python.exe" (
    echo Using bundled portable Python environment...
    "%~dp0python\python.exe" main.py
) else (
    echo Using system Python...
    python main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error code: %ERRORLEVEL%
    pause
)
