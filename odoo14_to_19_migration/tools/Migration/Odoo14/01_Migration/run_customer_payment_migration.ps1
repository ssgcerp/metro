param (
    [Parameter(Mandatory = $true)]
    [string]$CompanyName,

    [Parameter(Mandatory = $false)]
    [string]$ExcelMap = (Join-Path $PSScriptRoot "journal_mapping_o14.xlsx"),

    [Parameter(Mandatory = $false)]
    [int]$Limit = 1000
)

$ScriptPath = Join-Path $PSScriptRoot "migrate_o14_to_o19_payments_excel.py"

Write-Host "Starting Payment Migration for Company: $CompanyName" -ForegroundColor Cyan
Write-Host "Excel Map: $ExcelMap" -ForegroundColor Gray

# Run the python script
python $ScriptPath --company-name "$CompanyName" --excel-map "$ExcelMap" --limit $Limit

Write-Host "Migration Finished." -ForegroundColor Green
