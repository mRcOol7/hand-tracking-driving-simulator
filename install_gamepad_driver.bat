@echo off
title Install ViGEmBus Driver for ATS Virtual Controller
cd /d "%~dp0"

echo ========================================================
echo   Installing ViGEmBus Driver for Virtual Xbox 360 Controller
echo ========================================================
echo.

set "MSI_PATH=%~dp0python\Lib\site-packages\vgamepad\win\vigem\install\x64\ViGEmBusSetup_x64.msi"

if not exist "%MSI_PATH%" (
    set "MSI_PATH=%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages\vgamepad\win\vigem\install\x64\ViGEmBusSetup_x64.msi"
)

if exist "%MSI_PATH%" (
    echo Launching official driver installer...
    msiexec /i "%MSI_PATH%"
    echo.
    echo Installation finished. Restart your computer if required.
) else (
    echo Driver installer file not found.
)

pause
