@echo off
REM Batch file wrapper for AMC Contract Migration PowerShell script
REM Usage: Double-click this file or run from command prompt

echo Starting AMC Contract Migration...
echo.

REM Change to script directory
cd /d "%~dp0"

REM Run PowerShell script
powershell.exe -ExecutionPolicy Bypass -File "migrate_amc_contracts.ps1"

REM Keep window open on error
if errorlevel 1 (
    echo.
    echo Script completed with errors.
    pause
)

