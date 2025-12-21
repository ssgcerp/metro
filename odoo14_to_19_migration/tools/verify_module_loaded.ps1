# Script to verify if the module and controller are properly loaded
# This helps diagnose why the route might not be working

$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"

Write-Host "=== Module Loading Verification ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if we can access Odoo's module list via XML-RPC
Write-Host "Test 1: Checking module status via XML-RPC..." -ForegroundColor Yellow
try {
    # Try to connect via XML-RPC to check if module is installed
    $xmlrpcUrl = "$ODOO_URL/xmlrpc/2/common"
    $body = @"
<?xml version="1.0"?>
<methodCall>
    <methodName>authenticate</methodName>
    <params>
        <param><value><string>$DATABASE</string></value></param>
        <param><value><string>admin</string></value></param>
        <param><value><string>admin</string></value></param>
    </params>
</methodCall>
"@
    
    $response = Invoke-WebRequest -Uri $xmlrpcUrl -Method Post -Body $body -ContentType "text/xml" -UseBasicParsing
    Write-Host "✅ XML-RPC connection works" -ForegroundColor Green
} catch {
    Write-Host "⚠️  XML-RPC test skipped (not critical)" -ForegroundColor Yellow
}

Write-Host ""

# Test 2: Direct route test
Write-Host "Test 2: Testing migration route directly..." -ForegroundColor Yellow
Write-Host "URL: $ODOO_URL/migration/process_one?db=$DATABASE" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$ODOO_URL/migration/process_one?db=$DATABASE" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Route is WORKING!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Green
    Write-Host $response.Content
    Write-Host ""
    Write-Host "🎉 SUCCESS! The route is registered and working." -ForegroundColor Green
} catch {
    Write-Host "❌ Route still returns 404" -ForegroundColor Red
    Write-Host ""
    Write-Host "=== ACTION REQUIRED ===" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The route is NOT registered. You MUST:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. UPGRADE THE MODULE:" -ForegroundColor Cyan
    Write-Host "   a. Open Odoo: $ODOO_URL" -ForegroundColor White
    Write-Host "   b. Login to database: $DATABASE" -ForegroundColor White
    Write-Host "   c. Go to: Apps menu" -ForegroundColor White
    Write-Host "   d. Remove 'Apps' filter (click 'Apps' in top left)" -ForegroundColor White
    Write-Host "   e. Search: odoo14_to_19_migration" -ForegroundColor White
    Write-Host "   f. Click: 'Upgrade' button" -ForegroundColor White
    Write-Host "   g. Wait for upgrade to complete" -ForegroundColor White
    Write-Host ""
    Write-Host "2. RESTART ODOO SERVER:" -ForegroundColor Cyan
    Write-Host "   a. Stop Odoo server completely" -ForegroundColor White
    Write-Host "   b. Start Odoo server again" -ForegroundColor White
    Write-Host "   c. Wait for full startup" -ForegroundColor White
    Write-Host ""
    Write-Host "3. TEST AGAIN:" -ForegroundColor Cyan
    Write-Host "   Run this script again: .\verify_module_loaded.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        if ($responseBody) {
            Write-Host $responseBody -ForegroundColor Red
        }
    }
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
Write-Host "=== End Verification ===" -ForegroundColor Cyan

