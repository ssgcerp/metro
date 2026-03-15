@echo off
REM Batch file wrapper for migrate_invoices_continuous.ps1
REM This allows double-clicking to run the PowerShell script

powershell.exe -ExecutionPolicy Bypass -File "%~dp0migrate_invoices_continuous.ps1"
pause

