@echo off
echo Installing boto3 for Odoo...
echo.

REM Try to find Odoo Python path from common locations
set ODOO_PYTHON=

REM Check common Odoo installation paths
if exist "C:\Program Files\Odoo 19.0\python\python.exe" (
    set ODOO_PYTHON=C:\Program Files\Odoo 19.0\python\python.exe
)
if exist "C:\Odoo 19.0\python\python.exe" (
    set ODOO_PYTHON=C:\Odoo 19.0\python\python.exe
)
if exist "C:\odoo\python\python.exe" (
    set ODOO_PYTHON=C:\odoo\python\python.exe
)

if "%ODOO_PYTHON%"=="" (
    echo Odoo Python not found in common locations.
    echo Trying to use system Python...
    python -m pip install boto3
    if %errorlevel% equ 0 (
        echo boto3 installed successfully using system Python!
        pause
        exit /b 0
    ) else (
        echo.
        echo Please install boto3 manually:
        echo 1. Find your Odoo Python executable path
        echo 2. Run: [Odoo Python Path] -m pip install boto3
        echo.
        echo Or install using: python -m pip install boto3
        pause
        exit /b 1
    )
) else (
    echo Found Odoo Python at: %ODOO_PYTHON%
    echo Installing boto3...
    "%ODOO_PYTHON%" -m pip install boto3
    if %errorlevel% equ 0 (
        echo boto3 installed successfully!
    ) else (
        echo Failed to install boto3. Please check the Python path.
    )
    pause
)
