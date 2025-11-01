@echo off
title Odoo Service Controller
color 0A

:main
cls
echo ===========================================
echo          Odoo Service Controller
echo ===========================================
echo.
echo   [1] Odoo Server 19.0
echo   [2] Odoo Server 18.0
echo   [0] Exit
echo.
set /p choice=Select Odoo version: 

if "%choice%"=="1" set service=odoo-server-19.0&goto actions
if "%choice%"=="2" set service=odoo-server-18.0&goto actions
if "%choice%"=="0" exit
goto main

:actions
cls
echo ===========================================
echo     %service% - Service Controller
echo ===========================================
echo.
echo   [1] Start Service
echo   [2] Stop Service
echo   [3] Restart Service
echo   [0] Back
echo.
set /p action=Choose an action: 

if "%action%"=="1" goto start_service
if "%action%"=="2" goto stop_service
if "%action%"=="3" goto restart_service
if "%action%"=="0" goto main
goto actions

:start_service
echo Starting %service%...
net start "%service%"
pause
goto actions

:stop_service
echo Stopping %service%...
net stop "%service%"
pause
goto actions

:restart_service
echo Restarting %service%...
net stop "%service%"
timeout /t 2 >nul
net start "%service%"
pause
goto actions
