@echo off
REM Quick fix batch file to add branch_code column
REM Update database name and credentials below if needed

echo ========================================
echo Adding branch_code column to res_company
echo ========================================
echo.

cd "C:\Program Files\PostgreSQL\12\bin"

psql -U odoo -d metro1 -c "ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS! Column created.
    echo.
    echo Please RESTART your Odoo server now.
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR! Could not create column.
    echo.
    echo Please run manually:
    echo   ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);
    echo.
    echo In pgAdmin or any PostgreSQL client.
    echo ========================================
)

pause






