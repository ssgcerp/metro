# Check if the route is being called by looking at logs
# Run this AFTER trying to access the route from PowerShell

$logPath = "C:\Program Files\Odoo 19\server\odoo.log"

Write-Host "=== Checking if Route is Being Called ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "First, try accessing the route:" -ForegroundColor Yellow
Write-Host "Invoke-WebRequest -Uri 'http://localhost:8079/migration/process_one?db=metrodb' -UseBasicParsing" -ForegroundColor Gray
Write-Host ""
Write-Host "Then check the logs below..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path $logPath) {
    Write-Host "Checking last 50 lines for route call..." -ForegroundColor Yellow
    Write-Host ""
    
    $routeLogs = Get-Content $logPath -Tail 50 | Select-String -Pattern "process_one_quotation ROUTE CALLED|ROUTE CALLED|migration/process_one" -Context 2
    
    if ($routeLogs) {
        Write-Host "✅ Route IS being called!" -ForegroundColor Green
        Write-Host "This means Odoo is routing to the controller." -ForegroundColor Green
        Write-Host ""
        $routeLogs | ForEach-Object { Write-Host $_ -ForegroundColor White }
    } else {
        Write-Host "❌ Route is NOT being called" -ForegroundColor Red
        Write-Host "This means Odoo is rejecting the route before it reaches our code." -ForegroundColor Red
        Write-Host ""
        Write-Host "Possible causes:" -ForegroundColor Yellow
        Write-Host "1. Route not registered (module not upgraded/restarted)" -ForegroundColor White
        Write-Host "2. Odoo routing system blocking external access" -ForegroundColor White
        Write-Host "3. Database context required even with auth='none'" -ForegroundColor White
    }
} else {
    Write-Host "❌ Log file not found: $logPath" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== End Check ===" -ForegroundColor Cyan

