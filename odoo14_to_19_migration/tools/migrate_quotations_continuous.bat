@echo off
REM Batch file wrapper for Quotation Migration PowerShell script
REM This makes it easier to run the migration script

echo Starting Quotation Migration...
echo.

REM Run the PowerShell script
powershell.exe -ExecutionPolicy Bypass -File "%~dp0migrate_quotations_continuous.ps1"

REM Pause to see results if there was an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Migration script ended with an error.
    pause
)

