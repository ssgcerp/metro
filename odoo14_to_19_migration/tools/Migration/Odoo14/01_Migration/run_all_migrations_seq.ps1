$companies = @("ABU DHABI", "AJMAN", "DUBAI", "FUJAIRAH", "Ras Al Khaimah", "SHARJAH", "Unknown Branch")
$ExcelMap = "tools\Migration\journal_mapping_o14.xlsx"
$PythonScript = "tools\Migration\migrate_o14_to_o19_payments_excel.py"

foreach ($company in $companies) {
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host ">>> STARTING MIGRATION FOR: $company" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Cyan
    
    python $PythonScript --company-name "$company" --excel-map "$ExcelMap" --limit 1000
    
    Write-Host ">>> FINISHED MIGRATION FOR: $company" -ForegroundColor Green
    Write-Host ""
}
