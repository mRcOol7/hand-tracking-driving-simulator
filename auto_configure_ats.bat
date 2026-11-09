@echo off
title Auto Configure ATS Profile - 1:1 Hand Steering Wheel
cd /d "%~dp0"
echo ========================================================
echo   Auto-Configuring ATS Profile for 1:1 Hand Steering
echo ========================================================
echo.

if exist "%~dp0python\python.exe" (
    "%~dp0python\python.exe" auto_configure_ats.py
) else (
    python auto_configure_ats.py
)

echo.
pause

