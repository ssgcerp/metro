# Test both routes to verify controllers are working
# Run this after upgrading the module

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host "=== Testing Migration Routes ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Simple test route
Write-Host "Test 1: Testing simple route (/migration/test)..." -ForegroundColor Yellow
Write-Host "URL: $ODOO_URL/migration/test" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/test" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Test route is WORKING!" -ForegroundColor Green
    Write-Host "Response: $($response.Content.Trim())" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 Controllers are loading correctly!" -ForegroundColor Green
} catch {
    Write-Host "❌ Test route still returns 404" -ForegroundColor Red
    Write-Host "   This means controllers are NOT loading." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "   Next steps:" -ForegroundColor Yellow
    Write-Host "   1. Restart Odoo server" -ForegroundColor White
    Write-Host "   2. Check module path in odoo.conf" -ForegroundColor White
    Write-Host "   3. Check logs: .\check_controller_logs.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""

# Test 2: Migration process route
Write-Host "Test 2: Testing migration route (/migration/process_one)..." -ForegroundColor Yellow
Write-Host "URL: $ODOO_URL/migration/process_one?db=$DATABASE" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/process_one?db=$DATABASE" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Migration route is WORKING!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Green
    Write-Host $response.Content
    Write-Host ""
    Write-Host "🎉 SUCCESS! Both routes are working!" -ForegroundColor Green
} catch {
    Write-Host "❌ Migration route returned error" -ForegroundColor Red
    Write-Host ""
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "   404 Not Found - Route not registered" -ForegroundColor Red
    } else {
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            if ($responseBody) {
                Write-Host "   Response: $responseBody" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""
Write-Host "=== End Tests ===" -ForegroundColor Cyan

