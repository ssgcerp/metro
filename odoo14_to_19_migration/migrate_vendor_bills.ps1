# Vendor Bill Migration Script for Odoo 14 to Odoo 19 (PowerShell)
# This script helps with vendor bill migration tasks

param(
    [string]$Database = "odoo19",
    [string]$OdooBin = "odoo-bin",
    [string]$Config = "",
    [switch]$Check,
    [switch]$Status,
    [switch]$Upgrade,
    [switch]$TestConnection,
    [switch]$Logs,
    [switch]$All,
    [switch]$Help
)

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green "✓ $args" }
function Write-Error { Write-ColorOutput Red "✗ $args" }
function Write-Warning { Write-ColorOutput Yellow "⚠ $args" }
function Write-Info { Write-ColorOutput Cyan "ℹ $args" }
function Write-Header { 
    Write-ColorOutput Blue "========================================"
    Write-ColorOutput Blue "$args"
    Write-ColorOutput Blue "========================================"
}

function Show-Help {
    Write-Header "Vendor Bill Migration Script"
    Write-Output ""
    Write-Output "Usage: .\migrate_vendor_bills.ps1 [OPTIONS]"
    Write-Output ""
    Write-Output "Options:"
    Write-Output "  -Database <name>        Database name (default: odoo19)"
    Write-Output "  -OdooBin <path>        Path to odoo-bin (default: odoo-bin)"
    Write-Output "  -Check                 Check installation and modules"
    Write-Output "  -Status                View migration status"
    Write-Output "  -Upgrade               Upgrade migration module"
    Write-Output "  -TestConnection        Test Odoo 14 connection"
    Write-Output "  -Logs                  View migration logs"
    Write-Output "  -All                   Run all checks"
    Write-Output "  -Help                  Show this help message"
    Write-Output ""
    Write-Output "Examples:"
    Write-Output "  .\migrate_vendor_bills.ps1 -Check"
    Write-Output "  .\migrate_vendor_bills.ps1 -Status"
    Write-Output "  .\migrate_vendor_bills.ps1 -Upgrade"
    Write-Output "  .\migrate_vendor_bills.ps1 -All"
    Write-Output ""
}

function Check-Odoo {
    Write-Header "Checking Odoo Installation"
    
    if (Get-Command $OdooBin -ErrorAction SilentlyContinue) {
        $odooPath = (Get-Command $OdooBin).Source
        Write-Success "Odoo binary found: $odooPath"
    } else {
        Write-Error "Odoo binary not found. Please set -OdooBin parameter."
        exit 1
    }
}

function Check-Modules {
    Write-Header "Checking Required Modules"
    
    Write-Info "Required modules:"
    Write-Output "  - odoo14_to_19_migration"
    Write-Output "  - eq_fc_purchase_custom"
    Write-Output "  - eq_fc_invoice_custom"
    Write-Output "  - queue_job"
    Write-Output ""
    Write-Warning "Please check module installation in Odoo UI:"
    Write-Info "  Apps → Search for module name → Check if installed"
}

function Upgrade-Module {
    Write-Header "Upgrading Migration Module"
    
    Write-Info "To upgrade the module, run:"
    Write-Output ""
    Write-Output "  $OdooBin -d $Database -u odoo14_to_19_migration --stop-after-init"
    Write-Output ""
    Write-Info "Or use the Python script:"
    Write-Output "  python migrate_vendor_bills.py --upgrade -d $Database"
}

function Check-Config {
    Write-Header "Checking Migration Configuration"
    
    Write-Info "Please check migration configuration in Odoo UI:"
    Write-Output "  Odoo 14 Migration → Migration Configuration"
    Write-Output ""
    Write-Info "Or use the Python script:"
    Write-Output "  python migrate_vendor_bills.py --check -d $Database"
}

function View-Status {
    Write-Header "Vendor Bill Migration Status"
    
    Write-Info "Please check migration status in Odoo UI:"
    Write-Output "  Odoo 14 Migration → Vendors → Vendor Bills"
    Write-Output ""
    Write-Info "Or use the Python script:"
    Write-Output "  python migrate_vendor_bills.py --status -d $Database"
}

function Process-Queue {
    Write-Header "Processing Queue Jobs"
    
    Write-Info "Queue jobs are processed automatically by Odoo cron"
    Write-Output ""
    Write-Info "To manually process queue jobs, use Odoo shell:"
    Write-Output "  odoo shell -d $Database"
    Write-Output "  >>> env['queue.job'].process_jobs()"
}

function View-Logs {
    Write-Header "Viewing Migration Logs"
    
    $logFile = Join-Path $PSScriptRoot "logs\failed_vendor_bill_migrations.log"
    
    if (Test-Path $logFile) {
        Write-Info "Failed migrations log:"
        Write-Output ""
        Get-Content $logFile -Tail 50
    } else {
        Write-Warning "No failed migrations log found: $logFile"
    }
}

function Test-Connection {
    Write-Header "Testing Odoo 14 Connection"
    
    Write-Info "Please test connection in Odoo UI:"
    Write-Output "  Odoo 14 Migration → Migration Configuration → Test Connection"
    Write-Output ""
    Write-Info "Or use the Python script:"
    Write-Output "  python migrate_vendor_bills.py --test-connection -d $Database"
}

# Main execution
if ($Help) {
    Show-Help
    exit 0
}

if ($All) {
    Check-Odoo
    Check-Modules
    Check-Config
    View-Status
    Test-Connection
    View-Logs
} else {
    if ($Check) {
        Check-Odoo
        Check-Modules
        Check-Config
    }
    
    if ($Status) {
        View-Status
    }
    
    if ($Upgrade) {
        Upgrade-Module
    }
    
    if ($TestConnection) {
        Test-Connection
    }
    
    if ($Logs) {
        View-Logs
    }
    
    if (-not ($Check -or $Status -or $Upgrade -or $TestConnection -or $Logs)) {
        Show-Help
    }
}

