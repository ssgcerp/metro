@echo off
REM Batch file to run RFQ migration PowerShell script
SET SCRIPT_DIR=%~dp0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%migrate_rfq_continuous.ps1"
pause

