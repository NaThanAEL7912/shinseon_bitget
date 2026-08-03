@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================================
echo  [SHINSEON] Starting Shinseon Bitget Client...
echo ====================================================
echo.
echo  1. Checking for latest version updates...
python shinseon_updater.py --no-start
if %errorlevel% neq 0 (
    echo.
    echo ====================================================
    echo  [ERROR] Updater execution failed!
    echo ====================================================
    echo.
    pause
) else (
    start "" pythonw shinseon_client.pyw
)
exit
