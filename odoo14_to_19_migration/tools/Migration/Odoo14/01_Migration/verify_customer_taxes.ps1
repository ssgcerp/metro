param (
    [Parameter(Mandatory=$true)]
    [string]$CompanyName,
    
    [Parameter(Mandatory=$false)]
    [int]$Limit = 10000
)

$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "verify_fix_customer_invoice_taxes.py"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Odoo 14 -> Odoo 19 Customer Invoice Tax Verifier" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Company: $CompanyName"
Write-Host "Limit: $Limit"
Write-Host "----------------------------------------------------------"

# Execute the python script
python $scriptPath --company-name "$CompanyName" --limit $Limit

Write-Host "----------------------------------------------------------"
Write-Host "Execution Complete. Please check the generated Excel report." -ForegroundColor Green
Write-Host "The report contains columns for Odoo 14 Invoice Number, Odoo 19 Invoice Number,"
Write-Host "Original Odoo 14 Total, Odoo 19 Total Before, Final Odoo 19 Total, and Status."
