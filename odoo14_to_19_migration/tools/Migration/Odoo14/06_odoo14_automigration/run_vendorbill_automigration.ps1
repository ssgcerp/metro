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
Write-Host "===========================================================" -ForegroundColor Cyan

# 3. Run Migration Processing
Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "STEP 2: Processing Migration Queue" -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan

$MigrationScript = (Join-Path $ScriptDir "..\01_Migration\migrate_vendor_bills_continuous.ps1")

if (-not (Test-Path $MigrationScript)) {
    Write-Error "Migration script not found: $MigrationScript"
    exit
}

Write-Host "Starting vendor bill migration processing..."
& $MigrationScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Migration script exited with non-zero code ($LASTEXITCODE). Continuing to tax verification..." -ForegroundColor Yellow
}

Write-Host "`nMigration processing completed." -ForegroundColor Green

# 4. Verify and Fix Vendor Bill Taxes
Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "STEP 3: Verifying and Fixing Vendor Bill Taxes" -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan

$TaxVerifyScript = (Join-Path $ScriptDir "verify_fix_vendor_bill_taxes.py")

if (-not (Test-Path $TaxVerifyScript)) {
    Write-Error "Tax verification script not found: $TaxVerifyScript"
    exit
}

Write-Host "Running tax verification and fix..."
python $TaxVerifyScript --config "$ConfigFile"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Tax verification script exited with non-zero code ($LASTEXITCODE)." -ForegroundColor Yellow
} else {
    Write-Host "`nTax verification completed successfully." -ForegroundColor Green
}

Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "Fully Automated Migration Process Completed!" -ForegroundColor Cyan
Write-Host "Final Report:" -ForegroundColor Cyan
Write-Host " - See '..\00_Logs_and_Reports' for the missing bills Excel report." -ForegroundColor Cyan
Write-Host " - See Odoo 19 Vendor Bills menu -> Migration Lines for full logs." -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan

