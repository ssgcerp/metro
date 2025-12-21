# Quick test script to check if the migration URL is working
# Run this AFTER upgrading the module

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host "Testing migration URL..." -ForegroundColor Cyan
Write-Host "URL: $ODOO_URL/migration/process_one?db=$DATABASE" -ForegroundColor Yellow
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/process_one?db=$DATABASE" -UseBasicParsing
    Write-Host "✅ SUCCESS!" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "❌ ERROR:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Make sure module is UPGRADED (Apps → odoo14_to_19_migration → Upgrade)" -ForegroundColor Yellow
    Write-Host "2. Restart Odoo server after upgrade" -ForegroundColor Yellow
    Write-Host "3. Check database name is correct: $DATABASE" -ForegroundColor Yellow
}

