@echo off
title Dual Controller Verification Test
cd /d "%~dp0"

echo ========================================================
echo       ATS DUAL CONTROLLER SIMULATION TEST
echo ========================================================
echo.

if exist "python\python.exe" (
    echo Using bundled portable Python environment...
    python\python.exe test_dual_controller.py
) else (
    echo Using system Python environment...
    python test_dual_controller.py
)

echo.
pause

