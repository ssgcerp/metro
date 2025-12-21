@echo off
REM Migration Cron Batch File
REM Processes one quotation from the queue
REM Can be scheduled in Windows Task Scheduler

REM Configuration - Change these if needed
set ODOO_URL=http://localhost:8079
set ENDPOINT=/migration/process_one
set DATABASE=metrodb

REM Call the migration endpoint with database parameter
curl -s "%ODOO_URL%%ENDPOINT%?db=%DATABASE%"

REM Optional: Uncomment below to log output to file
REM curl -s "%ODOO_URL%%ENDPOINT%" >> C:\logs\migration.log 2>&1

REM Optional: Uncomment below to show timestamp
REM echo [%date% %time%] >> C:\logs\migration.log
