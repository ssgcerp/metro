@echo off
REM Continuous Migration Runner
REM Processes quotations one by one with delay between calls
REM Press Ctrl+C to stop

REM Configuration
set ODOO_URL=http://localhost:8079
set ENDPOINT=/migration/process_one
set DELAY_SECONDS=60
set LOG_FILE=C:\logs\migration_continuous.log

REM Create log directory if it doesn't exist
if not exist "C:\logs" mkdir C:\logs

echo Starting continuous migration...
echo URL: %ODOO_URL%%ENDPOINT%
echo Delay: %DELAY_SECONDS% seconds
echo Log: %LOG_FILE%
echo Press Ctrl+C to stop
echo.

:loop
    set TIMESTAMP=%date% %time%
    echo [%TIMESTAMP%] Processing... >> "%LOG_FILE%"
    curl -s "%ODOO_URL%%ENDPOINT%" >> "%LOG_FILE%" 2>&1
    echo. >> "%LOG_FILE%"
    
    REM Show last line in console
    for /f "tokens=*" %%a in ('curl -s "%ODOO_URL%%ENDPOINT%"') do echo [%time%] %%a
    
    REM Wait before next call
    timeout /t %DELAY_SECONDS% /nobreak >nul
goto loop
