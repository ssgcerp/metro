@echo off
REM Check Migration Status
REM Shows current migration status without processing

REM Configuration - Change these if needed
set ODOO_URL=http://localhost:8079
set ENDPOINT=/migration/status
set DATABASE=metrodb

REM Call the status endpoint
curl -s "%ODOO_URL%%ENDPOINT%?db=%DATABASE%"

REM Optional: Pretty print JSON (requires Python)
REM curl -s "%ODOO_URL%%ENDPOINT%" | python -m json.tool
