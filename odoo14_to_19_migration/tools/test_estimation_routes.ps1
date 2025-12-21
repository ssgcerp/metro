# Quick test script to verify estimation migration routes are available
# Uses same approach as migrate_one.ps1 - establish web session first
# Run this after upgrading the module to verify routes are working

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host ""
Write-Host "=== Testing Estimation Migration Routes ===" -ForegroundColor Cyan
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

# Test status route
Write-Host "Testing: /migration/status_estimation" -ForegroundColor Yellow
try {
    $statusUrl = "$ODOO_URL/migration/status_estimation?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $statusUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ Status route is working!" -ForegroundColor Green
    $json = $response.Content | ConvertFrom-Json
    Write-Host "  Queued: $($json.total_queued)" -ForegroundColor White
    Write-Host "  Migrating: $($json.migrating_now)" -ForegroundColor White
    Write-Host "  Migrated: $($json.total_migrated)" -ForegroundColor Green
    Write-Host "  Errors: $($json.total_errors)" -ForegroundColor Red
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 404) {
        Write-Host "  ❌ Route not found (404)" -ForegroundColor Red
        Write-Host "     Please upgrade the module: Apps > odoo14_to_19_migration > Upgrade" -ForegroundColor Yellow
        Write-Host "     Then FULLY restart Odoo server" -ForegroundColor Yellow
    } else {
        Write-Host "  ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""

# Test process route
Write-Host "Testing: /migration/process_one_estimation" -ForegroundColor Yellow
try {
    $processUrl = "$ODOO_URL/migration/process_one_estimation?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $processUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
    Write-Host "  ✅ Process route is working!" -ForegroundColor Green
    $response.Content -split "`n" | ForEach-Object {
        if ($_.Trim()) {
            Write-Host "  $_" -ForegroundColor White
        }
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 404) {
        Write-Host "  ❌ Route not found (404)" -ForegroundColor Red
        Write-Host "     Please upgrade the module: Apps > odoo14_to_19_migration > Upgrade" -ForegroundColor Yellow
        Write-Host "     Then FULLY restart Odoo server" -ForegroundColor Yellow
    } else {
        Write-Host "  ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host ""
