@echo off
:: Check for administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo Stopping Odoo Server 19.0 service...
net stop "odoo-server-19.0"
if %errorlevel% neq 0 (
    echo Failed to stop the service. It may already be stopped.
    pause
    exit /b %errorlevel%
)

echo Waiting for service to stop...
timeout /t 3 /nobreak >nul

echo Starting Odoo Server 19.0 service...
net start "odoo-server-19.0"
if %errorlevel% neq 0 (
    echo Failed to start the service. Please check the service status.
    pause
    exit /b %errorlevel%
)

echo Odoo Server 19.0 service restarted successfully!
pause

