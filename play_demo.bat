@echo off
title ATS Hand Steering - Highway Driving Demo
cd /d "%~dp0"

echo ========================================================
echo     AMERICAN TRUCK SIMULATOR - HIGHWAY ROAD DEMO
echo ========================================================
echo.

if exist "%~dp0python\python.exe" (
    "%~dp0python\python.exe" truck_sim_demo.py
) else (
    python truck_sim_demo.py
)

pause

