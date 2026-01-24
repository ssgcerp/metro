# Test accessing the route through Odoo's web interface
# Sometimes routes need to go through the web interface even with auth='none'

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host "=== Testing Routes Through Web Interface ===" -ForegroundColor Cyan
Write-Host ""

# Method 1: Access through web?db= first, then the route
Write-Host "Method 1: Accessing via web interface path..." -ForegroundColor Yellow
Write-Host "URL: $ODOO_URL/web?db=$DATABASE" -ForegroundColor Gray

try {
    # First, get a session by accessing the web interface
    $session = Invoke-WebRequest -Uri "$ODOO_URL/web?db=$DATABASE" -SessionVariable webSession -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Got web session" -ForegroundColor Green
    
    # Now try the migration route with the session
    Write-Host ""
    Write-Host "Testing migration route with session..." -ForegroundColor Yellow
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/process_one?db=$DATABASE" -WebSession $webSession -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Migration route works with session!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Method 2: Direct access (what we've been trying)
Write-Host "Method 2: Direct access (for comparison)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/process_one?db=$DATABASE" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Direct access works!" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "❌ Direct access failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== End Test ===" -ForegroundColor Cyan

