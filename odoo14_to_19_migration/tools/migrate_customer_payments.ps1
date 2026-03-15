# migrate_customer_payments.ps1
# This script executes the customer payment migration in Odoo 19

param (
    [switch]$DryRun = $false,
    [int]$Limit = 0
)

$PythonScript = "$PSScriptRoot\migrate_customer_payments.py"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Odoo 18 to 19 Customer Payment Migration " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "Mode: DRY RUN (No changes will be saved to Odoo 19)" -ForegroundColor Yellow
}
else {
    Write-Host "Mode: LIVE RUN (Changes WILL be saved to Odoo 19)" -ForegroundColor Red
}

if ($Limit -gt 0) {
    Write-Host "Limit: $Limit records" -ForegroundColor Yellow
}
else {
    Write-Host "Limit: ALL records" -ForegroundColor Yellow
}

Write-Host "---------------------------------------------" -ForegroundColor Cyan

# Build arguments for Python script
$argsList = @()
if (-not $DryRun) {
    $argsList += "--run"
}
if ($Limit -gt 0) {
    $argsList += "--limit"
    $argsList += $Limit
}
else {
    # Large arbitrary limit to fetch all records
    $argsList += "--limit"
    $argsList += 1000000 
}

Write-Host "Executing Python script... please wait."
python $PythonScript @argsList

if ($LASTEXITCODE -eq 0) {
    Write-Host "Migration script completed successfully." -ForegroundColor Green
    Write-Host "Check the generated Excel file for the result report." -ForegroundColor Green
}
else {
    Write-Host "Migration script encountered an error." -ForegroundColor Red
}

Write-Host "Done."
