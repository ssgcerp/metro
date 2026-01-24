# Diagnostic script to check if migration route is registered
# This helps identify why the route might not be working

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host "=== Migration Route Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if Odoo is running
Write-Host "Test 1: Checking if Odoo is accessible..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/web/database/selector" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Odoo is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Cannot reach Odoo at $ODOO_URL" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: Try the migration route
Write-Host "Test 2: Testing migration route..." -ForegroundColor Yellow
Write-Host "URL: $ODOO_URL/migration/process_one?db=$DATABASE" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/process_one?db=$DATABASE" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Route is working!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "❌ Route not found (404)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible causes:" -ForegroundColor Yellow
    Write-Host "1. Module not upgraded:" -ForegroundColor Yellow
    Write-Host "   → Go to Apps → Search 'odoo14_to_19_migration' → Click 'Upgrade'" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Odoo not restarted after upgrade:" -ForegroundColor Yellow
    Write-Host "   → Restart Odoo server completely" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Controller not loading:" -ForegroundColor Yellow
    Write-Host "   → Check Odoo logs for import errors" -ForegroundColor White
    Write-Host "   → Look for: 'odoo14_to_19_migration.controllers'" -ForegroundColor White
    Write-Host ""
    Write-Host "4. Wrong database name:" -ForegroundColor Yellow
    Write-Host "   → Current database: $DATABASE" -ForegroundColor White
    Write-Host "   → Verify in Odoo: Settings → Database → Database Manager" -ForegroundColor White
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host $responseBody -ForegroundColor Red
    } else {
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== End Diagnostic ===" -ForegroundColor Cyan

