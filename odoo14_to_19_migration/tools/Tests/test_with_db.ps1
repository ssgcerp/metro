# Test route with database parameter to see if that helps
# Sometimes Odoo needs the database even with auth='none'

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host "=== Testing Routes with Database Parameter ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Test route with db parameter
Write-Host "Test 1: /migration/test?db=$DATABASE" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/test?db=$DATABASE" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Works with db parameter!" -ForegroundColor Green
    Write-Host "Response: $($response.Content.Trim())" -ForegroundColor Green
} catch {
    Write-Host "❌ Still 404 even with db parameter" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 2: Migration route (should work)
Write-Host "Test 2: /migration/process_one?db=$DATABASE" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/process_one?db=$DATABASE" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Migration route works!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "❌ Migration route error" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        if ($responseBody) {
            Write-Host "Response: $responseBody" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "=== End Test ===" -ForegroundColor Cyan

