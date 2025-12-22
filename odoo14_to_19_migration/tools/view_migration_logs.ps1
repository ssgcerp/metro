# View RFQ Migration Logs
# This script helps you view migration logs in real-time

param(
    [string]$LogFile = "",
    [switch]$FailedOnly = $false,
    [int]$Tail = 100
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RFQ Migration Log Viewer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# If no log file specified, try to find Odoo log
if ([string]::IsNullOrEmpty($LogFile)) {
    $possiblePaths = @(
        "C:\Program Files\Odoo 19\server\odoo.log",
        "C:\Odoo\odoo.log",
        ".\odoo.log",
        "..\odoo.log"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $LogFile = $path
            Write-Host "Found Odoo log at: $LogFile" -ForegroundColor Green
            break
        }
    }
    
    if ([string]::IsNullOrEmpty($LogFile)) {
        Write-Host "Could not find Odoo log file automatically." -ForegroundColor Yellow
        Write-Host "Please specify the log file path:" -ForegroundColor Yellow
        Write-Host "  .\view_migration_logs.ps1 -LogFile 'C:\path\to\odoo.log'" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Or view failed migrations log:" -ForegroundColor Yellow
        Write-Host "  .\view_migration_logs.ps1 -FailedOnly" -ForegroundColor Cyan
        exit
    }
}

if ($FailedOnly) {
    $failedLog = "e:\odoo modules\19\metro\odoo14_to_19_migration\logs\failed_rfq_migrations.log"
    if (Test-Path $failedLog) {
        Write-Host "=== Failed RFQ Migrations ===" -ForegroundColor Red
        Write-Host ""
        Get-Content $failedLog -Tail $Tail
        Write-Host ""
        Write-Host "To follow in real-time, run:" -ForegroundColor Yellow
        Write-Host "  Get-Content '$failedLog' -Wait -Tail 20" -ForegroundColor Cyan
    } else {
        Write-Host "Failed migrations log not found at: $failedLog" -ForegroundColor Red
    }
    exit
}

Write-Host "Viewing migration logs from: $LogFile" -ForegroundColor Green
Write-Host "Filtering for: odoo14_to_19_migration, PRODUCT LINE, RFQ, migration" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# View logs with filtering
Get-Content $LogFile -Wait -Tail $Tail | Select-String -Pattern "odoo14_to_19_migration|PRODUCT LINE|RFQ|migration|Step|Created RFQ|Failed|ERROR|CRITICAL" -CaseSensitive:$false

