# Test the migration route now that we know controllers are working

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host "=== Testing Migration Route ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Testing: $ODOO_URL/migration/process_one?db=$DATABASE" -ForegroundColor Yellow
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/process_one?db=$DATABASE" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Migration route is WORKING!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Green
    Write-Host $response.Content
    Write-Host ""
    Write-Host "🎉 SUCCESS! The migration route is now working!" -ForegroundColor Green
} catch {
    Write-Host "❌ Migration route error" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode
        Write-Host "Status Code: $statusCode" -ForegroundColor Red
        
        if ($statusCode -eq 404) {
            Write-Host ""
            Write-Host "404 means route not found. But test route works, so:" -ForegroundColor Yellow
            Write-Host "1. Make sure you're using: ?db=$DATABASE" -ForegroundColor White
            Write-Host "2. Check if database name is correct" -ForegroundColor White
        } else {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            if ($responseBody) {
                Write-Host "Response: $responseBody" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""
Write-Host "=== End Test ===" -ForegroundColor Cyan

