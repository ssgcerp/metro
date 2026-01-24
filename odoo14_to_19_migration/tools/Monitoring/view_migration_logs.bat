@echo off
REM View RFQ Migration Logs - Batch wrapper
powershell.exe -ExecutionPolicy Bypass -File "%~dp0view_migration_logs.ps1" %*

