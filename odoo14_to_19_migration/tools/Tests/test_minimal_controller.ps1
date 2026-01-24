# Test minimal controller to verify basic controller loading
# Uses same approach as migrate_one.ps1 - establish web session first

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host ""
Write-Host "=== Testing Minimal Controller ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Establish database session (like migrate_one.ps1 does)
Write-Host "Establishing database session..." -ForegroundColor Gray
try {
    $null = Invoke-WebRequest -Uri "$ODOO_URL/web?db=$DATABASE" -SessionVariable webSession -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ Session established" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Failed to establish session: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "Test 1: /migration/minimal_test (auth='public')" -ForegroundColor Yellow
try {
    $url = "$ODOO_URL/migration/minimal_test?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $url -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ SUCCESS! Controller is loading!" -ForegroundColor Green
    Write-Host "  Response: $($response.Content.Trim())" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  ❌ Failed (Status: $statusCode)" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "Test 2: /migration/test (original test route)" -ForegroundColor Yellow
try {
    $url = "$ODOO_URL/migration/test?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $url -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ SUCCESS! Original test route works!" -ForegroundColor Green
    Write-Host "  Response: $($response.Content.Trim())" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  ❌ Failed (Status: $statusCode)" -ForegroundColor Red
}
Write-Host ""

Write-Host "Test 3: /migration/status (quotation route)" -ForegroundColor Yellow
try {
    $url = "$ODOO_URL/migration/status?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $url -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ SUCCESS! Quotation route works!" -ForegroundColor Green
    Write-Host "  Response preview: $($response.Content.Substring(0, [Math]::Min(100, $response.Content.Length)))" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  ❌ Failed (Status: $statusCode)" -ForegroundColor Red
}
Write-Host ""

Write-Host "=== Interpretation ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "If Test 1 works:" -ForegroundColor Yellow
Write-Host "  ✅ Controllers ARE loading - issue is with auth='none' routes" -ForegroundColor Green
Write-Host "  → We need to change auth='none' to auth='public'" -ForegroundColor White
Write-Host ""
Write-Host "If both fail with 404:" -ForegroundColor Yellow
Write-Host "  ❌ Controllers are NOT loading at all" -ForegroundColor Red
Write-Host "  → Need to check Odoo logs for import errors" -ForegroundColor White
Write-Host "  → Need to reinstall module and restart server" -ForegroundColor White
Write-Host ""

