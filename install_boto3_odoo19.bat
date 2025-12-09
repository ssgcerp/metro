@echo off
echo Installing boto3 for Odoo 19...
echo.
echo Python path: C:\Program Files\Odoo 19\python\python.exe
echo.

"C:\Program Files\Odoo 19\python\python.exe" -m pip install boto3 botocore s3transfer

if %errorlevel% equ 0 (
    echo.
    echo boto3 installation completed!
    echo.
    echo Verifying installation...
    "C:\Program Files\Odoo 19\python\python.exe" -c "import boto3; print('boto3 version:', boto3.__version__)"
) else (
    echo.
    echo Installation failed with error code: %errorlevel%
    echo.
    echo Trying with --user flag...
    "C:\Program Files\Odoo 19\python\python.exe" -m pip install --user boto3
)

echo.
echo Checking if boto3 is installed...
dir "C:\Program Files\Odoo 19\python\Lib\site-packages\boto3" 2>nul
if %errorlevel% equ 0 (
    echo boto3 folder found!
) else (
    echo boto3 folder NOT found in site-packages.
)

pause
