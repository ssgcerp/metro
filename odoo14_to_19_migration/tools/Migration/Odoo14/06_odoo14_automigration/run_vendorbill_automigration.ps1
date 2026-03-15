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

Write-Host "`nPython analysis completed successfully." -ForegroundColor Green


# 3. Reading Configuration for API calls
$ConfigRaw = Get-Content $ConfigFile -Raw
$Config = $ConfigRaw | ConvertFrom-Json
$Odoo19Url = $Config.odoo19.url + "/migration/status_vendor_bill"
$Odoo19ProcessUrl = $Config.odoo19.url + "/migration/process_one_vendor_bill"

# Optional: Add Basic Auth if URL endpoints are protected (usually not for these specific custom routes)
# We will just do a standard Invoke-RestMethod. If it requires auth, it would throw 401.

# 4. Continuous Processing
Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "STEP 2: Processing Migration Queue" -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan

$ConsecutiveErrors = 0
$EmptyQueueCount = 0

while ($true) {
    try {
        # Check overall status
        $StatusResponse = Invoke-RestMethod -Uri $Odoo19Url -Method Get -ErrorAction Stop
        
        $Queued = $StatusResponse.queued
        $Migrating = $StatusResponse.migrating
        $Migrated = $StatusResponse.migrated
        $Errors = $StatusResponse.error
        
        Write-Host "[Status] Queued: $Queued | Migrating: $Migrating | Migrated: $Migrated | Errors: $Errors"
        
        if ($Queued -gt 0) {
            # Reset counters
            $ConsecutiveErrors = 0
            $EmptyQueueCount = 0
            
            Write-Host "Processing 1 bill from the queue..." -NoNewline
            $ProcessResponse = Invoke-RestMethod -Uri $Odoo19ProcessUrl -Method Get -TimeoutSec 120 -ErrorAction Stop
            
            if ($ProcessResponse.success) {
                Write-Host " Success: $($ProcessResponse.bill_number)" -ForegroundColor Green
            } else {
                Write-Host " Failed: $($ProcessResponse.error)" -ForegroundColor Red
            }
        } else {
            # No queued bills found
            $EmptyQueueCount++
            Write-Host "No bills in queue. Waiting 5s... (Attempt $EmptyQueueCount/3)" -ForegroundColor Yellow
            Start-Sleep -Seconds 5
            
            if ($EmptyQueueCount -ge 3) {
                Write-Host "`nQueue is completely empty. Migration process finished." -ForegroundColor Green
                break
            }
        }
    }
    catch {
        $ConsecutiveErrors++
        $ErrorMessage = $_.Exception.Message
        Write-Host "`nERROR connecting to Odoo 19: $ErrorMessage" -ForegroundColor Red
        
        if ($ConsecutiveErrors -ge 5) {
            Write-Host "Too many consecutive errors ($ConsecutiveErrors). Stopping migration process." -ForegroundColor Red
            break
        }
        
        Write-Host "Retrying in 10 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
}

Write-Host "`n===========================================================" -ForegroundColor Cyan
Write-Host "Fully Automated Migration Process Completed!" -ForegroundColor Cyan
Write-Host "Final Report:" -ForegroundColor Cyan
Write-Host " - See '..\00_Logs_and_Reports' for the missing bills Excel report." -ForegroundColor Cyan
Write-Host " - See Odoo 19 Vendor Bills menu -> Migration Lines for full logs." -ForegroundColor Cyan
Write-Host "===========================================================`n" -ForegroundColor Cyan
