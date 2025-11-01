# Git Pull from Server and Restart Docker
# This script connects to the server, pulls latest changes, and restarts Docker services

$ErrorActionPreference = "Stop"

Write-Host "=== Git Pull from Server and Restart Docker ===" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PLINK_PATH = "C:\Program Files\PuTTY\plink.exe"
$SSH_USER = "root"
$SSH_HOST = "103.174.102.105"
$SSH_PASS = "Amaze@321"
$GIT_USER = "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"
$GIT_PASS = "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"
$GIT_REPO = "https://github.com/ssgcerp/metro.git"
$REPO_PATH = "/opt/odoo19/metro"

# Check if plink exists
if (-not (Test-Path $PLINK_PATH)) {
    Write-Host "Error: plink.exe not found at $PLINK_PATH" -ForegroundColor Red
    Write-Host "Please install PuTTY or update the PLINK_PATH variable." -ForegroundColor Yellow
    exit 1
}

Write-Host "Connecting to $SSH_HOST..." -ForegroundColor Yellow

try {
    # First verify the directory exists and show current path for debugging
    Write-Host "Verifying repository path..." -ForegroundColor Yellow
    $checkCommand = "bash -l -c `"if [ -d $REPO_PATH ]; then echo 'Directory exists: $REPO_PATH'; pwd; ls -la $REPO_PATH/.git 2>&1 | head -1; else echo 'Directory does not exist: $REPO_PATH'; fi`""
    & $PLINK_PATH -ssh "${SSH_USER}@${SSH_HOST}" -pw $SSH_PASS $checkCommand
    Write-Host ""
    
    # Build the command to git pull and restart Docker
    # Using explicit cd with error checking
    Write-Host "Executing git pull and Docker restart commands..." -ForegroundColor Yellow
    Write-Host ""
    
    # Build the bash command with proper escaping and error checking
    $gitCommand = "cd $REPO_PATH || { echo 'ERROR: Failed to change to directory $REPO_PATH'; exit 1; } && pwd && git pull && sudo docker-compose restart && sudo docker restart odoo19"
    
    $remoteCommand = "bash -l -c `"$gitCommand`""
    & $PLINK_PATH -ssh "${SSH_USER}@${SSH_HOST}" -pw $SSH_PASS $remoteCommand
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Git pull and Docker restart completed successfully" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Command execution failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host ""
    Write-Host "Error executing commands: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan

