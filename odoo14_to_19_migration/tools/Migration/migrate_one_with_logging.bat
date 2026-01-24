@echo off
REM Migration Cron Batch File with Logging
REM Processes one quotation and logs the result

REM Configuration - Change these if needed
set ODOO_URL=http://localhost:8079
set ENDPOINT=/migration/process_one
set DATABASE=metrodb
set LOG_FILE=C:\logs\migration.log

REM Create log directory if it doesn't exist
if not exist "C:\logs" mkdir C:\logs

REM Get timestamp
set TIMESTAMP=%date% %time%

REM Call the migration endpoint and log output
echo [%TIMESTAMP%] Processing migration... >> "%LOG_FILE%"
curl -s "%ODOO_URL%%ENDPOINT%?db=%DATABASE%" >> "%LOG_FILE%" 2>&1
echo. >> "%LOG_FILE%"

REM Optional: Also show in console
REM curl -s "%ODOO_URL%%ENDPOINT%?db=%DATABASE%"
