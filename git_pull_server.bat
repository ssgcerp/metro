@echo off

REM =====================================================
REM Git Pull from Server and Restart Docker
REM Automated script using PuTTY plink
REM =====================================================

REM --------- Configuration ---------
set "PLINK_PATH=C:\Program Files\PuTTY\plink.exe"
set "SSH_USER=root"
set "SSH_HOST=103.174.102.105"
set "SSH_PASS=Amaze@321"
set "GIT_USER=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"
set "GIT_PASS=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"
set "GIT_REPO=https://github.com/ssgcerp/metro.git"
set "REPO_PATH=/opt/odoo19/metro"

REM --------- Check if plink exists ---------
if not exist "%PLINK_PATH%" (
    echo Error: plink.exe not found at %PLINK_PATH%
    echo Please install PuTTY or update the PLINK_PATH variable.
    pause
    exit /b 1
)

echo === Git Pull from Server and Restart Docker ===
echo.
echo Connecting to %SSH_HOST%...
echo.

REM --------- Verify repository path ---------
echo Verifying repository path...
"%PLINK_PATH%" -ssh %SSH_USER%@%SSH_HOST% -pw %SSH_PASS% ^
"bash -l -c \"if [ -d %REPO_PATH% ]; then echo 'Directory exists: %REPO_PATH%'; pwd; ls -la %REPO_PATH%/.git 2>&1 | head -1; else echo 'Directory does not exist: %REPO_PATH%'; fi\""

echo.
echo Executing git pull and Docker restart commands...
echo.

REM --------- Execute git pull and Docker restart ---------
"%PLINK_PATH%" -ssh %SSH_USER%@%SSH_HOST% -pw %SSH_PASS% ^
"bash -l -c \"cd %REPO_PATH% || { echo 'ERROR: Failed to change to directory %REPO_PATH%'; exit 1; } && pwd && git pull && sudo docker-compose restart && sudo docker restart odoo19\""

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Git pull and Docker restart completed successfully
) else (
    echo.
    echo Command execution failed with exit code %ERRORLEVEL%
    pause
    exit /b 1
)

echo.
echo === Done ===
pause

