# Check Odoo logs for controller loading messages
# This helps verify if the controller is being loaded

$logPath = "C:\Program Files\Odoo 19\server\odoo.log"

Write-Host "=== Checking Odoo Logs for Controller Loading ===" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $logPath) {
    Write-Host "Reading last 200 lines of log file..." -ForegroundColor Yellow
    Write-Host ""
    
    # Check for controller loading messages
    $controllerLogs = Get-Content $logPath -Tail 200 | Select-String -Pattern "MigrationCronController|migration_cron|controllers" -Context 2
    
    if ($controllerLogs) {
        Write-Host "✅ Found controller-related logs:" -ForegroundColor Green
        Write-Host ""
        $controllerLogs | ForEach-Object { Write-Host $_ -ForegroundColor White }
    } else {
        Write-Host "❌ No controller loading messages found" -ForegroundColor Red
        Write-Host ""
        Write-Host "This means the controller is NOT being loaded." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Possible causes:" -ForegroundColor Yellow
        Write-Host "1. Module not in Odoo's addons path" -ForegroundColor White
        Write-Host "2. Module not upgraded properly" -ForegroundColor White
        Write-Host "3. Import error preventing controller from loading" -ForegroundColor White
        Write-Host ""
        Write-Host "Check the full log for errors:" -ForegroundColor Yellow
        Write-Host "Get-Content '$logPath' -Tail 50" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "=== Checking for any errors ===" -ForegroundColor Cyan
    $errors = Get-Content $logPath -Tail 200 | Select-String -Pattern "ERROR|Error|Traceback|Exception" -Context 1
    
    if ($errors) {
        Write-Host "⚠️  Found errors in logs:" -ForegroundColor Yellow
        $errors | Select-Object -First 10 | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    } else {
        Write-Host "✅ No recent errors found" -ForegroundColor Green
    }
} else {
    Write-Host "❌ Log file not found at: $logPath" -ForegroundColor Red
    Write-Host "Please check the Odoo log file path in your configuration." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== End Log Check ===" -ForegroundColor Cyan

