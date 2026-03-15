param (
    [Parameter(Mandatory=$false)]
    [int]$Limit = 10000
)

$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "verify_fix_vendor_bill_taxes_o18.py"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Odoo 18 -> Odoo 19 Vendor Bill Tax Verifier (All)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Scope: ALL Companies"
Write-Host "Limit: $Limit"
Write-Host "----------------------------------------------------------"

python $scriptPath --limit $Limit

Write-Host "----------------------------------------------------------"
Write-Host "Execution Complete. Please check the generated Excel report." -ForegroundColor Green
Write-Host "The report contains columns for Odoo 18 Bill Number, Odoo 19 Bill Number,"
Write-Host "Original Odoo 18 Total, Odoo 19 Total Before, Final Odoo 19 Total, and Status."
