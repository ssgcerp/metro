# Diagnostic script to check if migration controller is loading
# This helps identify if the issue is with controller loading or route registration

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host ""
Write-Host "=== Controller Loading Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if test route works (this should work if controllers load)
Write-Host "Test 1: Testing /migration/test route..." -ForegroundColor Yellow
try {
    $testUrl = "$ODOO_URL/migration/test?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $testUrl -Method Get -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ Test route works - controllers are loading!" -ForegroundColor Green
    Write-Host "  Response: $($response.Content)" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  ❌ Test route failed (Status: $statusCode)" -ForegroundColor Red
    Write-Host "     This suggests controllers might not be loading" -ForegroundColor Yellow
}
Write-Host ""

# Test 2: Check quotation routes (existing routes)
Write-Host "Test 2: Testing /migration/status route (quotation)..." -ForegroundColor Yellow
try {
    $statusUrl = "$ODOO_URL/migration/status?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $statusUrl -Method Get -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ Quotation status route works!" -ForegroundColor Green
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  ❌ Quotation route failed (Status: $statusCode)" -ForegroundColor Red
    if ($statusCode -eq 404) {
        Write-Host "     Even existing routes are 404 - server might need restart" -ForegroundColor Yellow
    }
}
Write-Host ""

# Test 3: Check estimation routes (new routes)
Write-Host "Test 3: Testing /migration/status_estimation route..." -ForegroundColor Yellow
try {
    $estStatusUrl = "$ODOO_URL/migration/status_estimation?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $estStatusUrl -Method Get -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ Estimation status route works!" -ForegroundColor Green
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  ❌ Estimation route failed (Status: $statusCode)" -ForegroundColor Red
    if ($statusCode -eq 404) {
        Write-Host "     Route not registered - module needs upgrade OR server restart" -ForegroundColor Yellow
    }
}
Write-Host ""

Write-Host "=== Recommendations ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "If all routes return 404:" -ForegroundColor Yellow
Write-Host "  1. FULLY RESTART Odoo server (not just upgrade)" -ForegroundColor White
Write-Host "  2. Check Odoo logs for any Python errors" -ForegroundColor White
Write-Host "  3. Verify module is installed (not just upgraded)" -ForegroundColor White
Write-Host ""
Write-Host "If only estimation routes return 404:" -ForegroundColor Yellow
Write-Host "  1. Upgrade module: Apps > odoo14_to_19_migration > Upgrade" -ForegroundColor White
Write-Host "  2. Restart Odoo server" -ForegroundColor White
Write-Host ""
Write-Host "=== End Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

