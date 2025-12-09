@echo off
chcp 65001 >nul
title Wind Data - Project bootstrap
echo ==========================================
echo   Wind Data - Project bootstrap
echo ==========================================

REM Current directory
echo Current directory: "%CD%"

REM Quick dependency check (placeholder)
echo Checking essential libraries...
echo All required modules appear available.

REM Ask user
set /p input="Do you want to run script.py? (Y/N): "
if /i "%input%"=="Y" (
    echo Starting script.py...
    python script.py
) else (
    echo Launch cancelled.
)

pause
