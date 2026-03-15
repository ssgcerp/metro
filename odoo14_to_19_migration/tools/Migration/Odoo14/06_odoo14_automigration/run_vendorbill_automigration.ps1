<#
.SYNOPSIS
    Fully automated Vendor Bill Migration Script for Odoo 14 to Odoo 19.

.DESCRIPTION
    This script orchestrates the entire migration process:
    1. Loads credentials from configuration
    2. Runs the Python script to compare environments, find missing bills, map journals from Excel, and queue them into Odoo 19.
    3. Continuously monitors the Odoo 19 migration queue until completed.
#>

$ErrorActionPreference = "Stop"

# Get current script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Activate Virtual Environment
$VenvPath = (Join-Path $ScriptDir "..\..\.venvScripts")
if (Test-Path $VenvPath) {
    Write-Host "Activating Python Virtual Environment from $VenvPath..." -ForegroundColor Cyan
    & "$VenvPath\Activate.ps1"
} else {
    Write-Host "Warning: Virtual environment not found at $VenvPath. Continuing with system Python." -ForegroundColor Yellow
}

# 2. Run Python Queue Script
Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "STEP 1: Checking Missing Bills and Queuing Migration Lines" -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan

$PythonScript = (Join-Path $ScriptDir "auto_queue_vendor_bills.py")
$ConfigFile = (Join-Path $ScriptDir "migration_config.json")
$MappingFile = (Join-Path $ScriptDir "..\00_Logs_and_Reports\journal_mapping_o14.xlsx")

if (-not (Test-Path $PythonScript)) {
    Write-Error "Python script not found: $PythonScript"
    exit
}

if (-not (Test-Path $ConfigFile)) {
    Write-Error "Configuration file not found: $ConfigFile"
    exit
}

Write-Host "Executing Python script to analyze and queue bills..."
python $PythonScript --config "$ConfigFile" --mapping "$MappingFile"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Python script failed. Stopping migration process."
    exit
}

Write-Host "`nPython analysis completed successfully. Bills have been queued." -ForegroundColor Green

Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "Queuing Complete — Migration NOT Started" -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan
Write-Host " - Bills have been queued in Odoo 19 but migration has NOT been triggered." -ForegroundColor Yellow
Write-Host " - See '..\00_Logs_and_Reports' for the missing bills Excel report." -ForegroundColor Cyan
Write-Host " - To start migration, use the Odoo 19 UI or run the processing step separately." -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan
