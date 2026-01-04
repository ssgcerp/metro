@echo off
REM Vendor Bill Migration Script for Odoo 14 to Odoo 19 (Windows Batch)
REM This script helps with vendor bill migration tasks

setlocal enabledelayedexpansion

set DATABASE=odoo19
set ODOO_BIN=odoo-bin

if "%1"=="" goto :menu
if "%1"=="--help" goto :help
if "%1"=="-h" goto :help
if "%1"=="--check" goto :check
if "%1"=="-c" goto :check
if "%1"=="--status" goto :status
if "%1"=="-s" goto :status
if "%1"=="--upgrade" goto :upgrade
if "%1"=="-u" goto :upgrade
if "%1"=="--logs" goto :logs
if "%1"=="-l" goto :logs
if "%1"=="--all" goto :all
if "%1"=="-a" goto :all
goto :menu

:help
echo Vendor Bill Migration Script
echo.
echo Usage: migrate_vendor_bills.bat [OPTION]
echo.
echo Options:
echo   --check, -c      Check installation and modules
echo   --status, -s     View migration status
echo   --upgrade, -u    Upgrade migration module
echo   --logs, -l       View migration logs
echo   --all, -a        Run all checks
echo   --help, -h       Show this help message
echo.
echo Examples:
echo   migrate_vendor_bills.bat --check
echo   migrate_vendor_bills.bat --status
echo   migrate_vendor_bills.bat --upgrade
echo.
goto :end

:check
echo ========================================
echo Checking Installation
echo ========================================
echo.
echo Checking Odoo binary...
where %ODOO_BIN% >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Odoo binary found
) else (
    echo [ERROR] Odoo binary not found: %ODOO_BIN%
    echo Please set ODOO_BIN environment variable
)
echo.
echo Checking required modules...
echo   - odoo14_to_19_migration
echo   - eq_fc_purchase_custom
echo   - eq_fc_invoice_custom
echo   - queue_job
echo.
echo Please check module installation in Odoo UI:
echo   Apps -^> Search for module name -^> Check if installed
echo.
goto :end

:status
echo ========================================
echo Vendor Bill Migration Status
echo ========================================
echo.
echo Please check migration status in Odoo UI:
echo   Odoo 14 Migration -^> Vendors -^> Vendor Bills
echo.
echo Or use the Python script:
echo   python migrate_vendor_bills.py --status -d %DATABASE%
echo.
goto :end

:upgrade
echo ========================================
echo Upgrading Migration Module
echo ========================================
echo.
echo To upgrade the module, run:
echo   %ODOO_BIN% -d %DATABASE% -u odoo14_to_19_migration --stop-after-init
echo.
echo Or use the Python script:
echo   python migrate_vendor_bills.py --upgrade -d %DATABASE%
echo.
goto :end

:logs
echo ========================================
echo Viewing Migration Logs
echo ========================================
echo.
if exist "logs\failed_vendor_bill_migrations.log" (
    echo Last 20 entries from log file:
    echo ----------------------------------------
    powershell -Command "Get-Content 'logs\failed_vendor_bill_migrations.log' -Tail 20"
) else (
    echo [WARNING] Log file not found: logs\failed_vendor_bill_migrations.log
)
echo.
goto :end

:all
call :check
echo.
call :status
echo.
call :upgrade
echo.
call :logs
goto :end

:menu
echo ========================================
echo Vendor Bill Migration Tool
echo ========================================
echo.
echo 1. Check Installation
echo 2. View Migration Status
echo 3. Upgrade Module
echo 4. View Logs
echo 5. Run All Checks
echo 0. Exit
echo.
set /p choice="Select an option: "

if "%choice%"=="1" goto :check
if "%choice%"=="2" goto :status
if "%choice%"=="3" goto :upgrade
if "%choice%"=="4" goto :logs
if "%choice%"=="5" goto :all
if "%choice%"=="0" goto :end
echo Invalid option
goto :menu

:end
pause

