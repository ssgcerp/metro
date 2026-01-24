# PowerShell script for Real-Time Odoo Log Monitoring
# Watches Odoo log file and displays new entries in real-time
# Filters for vendor bill migration related entries

param(
    [string]$LogPath = "",
    [string]$Filter = "vendor.bill|vendor_bill|Vendor Bill|migration|cheque|Cheque|eq_cheque|eq.cheque",
    [switch]$All,
    [switch]$Errors,
    [switch]$Help
)

# Colors for output
function Write-LogLine {
    param([string]$Line, [string]$Color = "White")
    
    # Color coding based on log level
    if ($Line -match "ERROR|CRITICAL|Exception|Traceback") {
        Write-Host $Line -ForegroundColor "Red"
    } elseif ($Line -match "WARNING|WARN") {
        Write-Host $Line -ForegroundColor "Yellow"
    } elseif ($Line -match "INFO|✅|Successfully") {
        Write-Host $Line -ForegroundColor "Green"
    } elseif ($Line -match "DEBUG") {
        Write-Host $Line -ForegroundColor "Gray"
    } elseif ($Line -match "🔄|Starting|Processing") {
        Write-Host $Line -ForegroundColor "Cyan"
    } else {
        Write-Host $Line -ForegroundColor $Color
    }
}

function Show-Help {
    Write-Host ""
    Write-Host "Odoo Real-Time Log Monitor" -ForegroundColor "Cyan"
    Write-Host "=========================" -ForegroundColor "Cyan"
    Write-Host ""
    Write-Host "Usage: .\watch_odoo_logs.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -LogPath <path>     Path to Odoo log file"
    Write-Host "                      Default: Auto-detect common locations"
    Write-Host "  -Filter <pattern>   Filter log entries (regex pattern)"
    Write-Host "                      Default: 'vendor.bill|vendor_bill|Vendor Bill|migration|cheque|Cheque|eq_cheque|eq.cheque'"
    Write-Host "  -All                Show all log entries (no filtering)"
    Write-Host "  -Errors             Show only errors and warnings"
    Write-Host "  -Help               Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\watch_odoo_logs.ps1"
    Write-Host "  .\watch_odoo_logs.ps1 -LogPath 'C:\odoo\logs\odoo.log'"
    Write-Host "  .\watch_odoo_logs.ps1 -Filter 'migration|invoice'"
    Write-Host "  .\watch_odoo_logs.ps1 -Errors"
    Write-Host "  .\watch_odoo_logs.ps1 -All"
    Write-Host ""
}

function Find-OdooLogFile {
    # Common Odoo log file locations
    $possiblePaths = @(
        "C:\Program Files\Odoo 19\server\odoo.log",
        "C:\odoo\odoo.log",
        "D:\odoo\logs\odoo.log",
        "D:\odoo\odoo.log",
        "E:\odoo\logs\odoo.log",
        "E:\odoo\odoo.log",
        "$env:USERPROFILE\odoo\logs\odoo.log",
        "$env:USERPROFILE\odoo\odoo.log",
        ".\logs\odoo.log",
        ".\odoo.log"
    )
    
    # Also check if running from Odoo directory
    $currentDir = Get-Location
    $possiblePaths += @(
        "$currentDir\logs\odoo.log",
        "$currentDir\odoo.log",
        "$currentDir\..\logs\odoo.log",
        "$currentDir\..\odoo.log"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    return $null
}

if ($Help) {
    Show-Help
    exit 0
}

# Find log file if not specified
if (-not $LogPath) {
    $LogPath = Find-OdooLogFile
}

if (-not $LogPath -or -not (Test-Path $LogPath)) {
    Write-Host ""
    Write-Host "❌ Log file not found!" -ForegroundColor "Red"
    Write-Host ""
    Write-Host "Please specify log file path:" -ForegroundColor "Yellow"
    Write-Host "  .\watch_odoo_logs.ps1 -LogPath 'C:\path\to\odoo.log'" -ForegroundColor "Gray"
    Write-Host ""
    Write-Host "Or place the script in the Odoo directory where odoo.log exists" -ForegroundColor "Gray"
    Write-Host ""
    exit 1
}

# Adjust filter based on parameters
if ($All) {
    $Filter = ".*"
} elseif ($Errors) {
    $Filter = "ERROR|CRITICAL|WARNING|WARN|Exception|Traceback|Failed|Error"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor "Cyan"
Write-Host "Odoo Real-Time Log Monitor" -ForegroundColor "Cyan"
Write-Host "========================================" -ForegroundColor "Cyan"
Write-Host ""
Write-Host "Log File: $LogPath" -ForegroundColor "Yellow"
Write-Host "Filter: $Filter" -ForegroundColor "Yellow"
Write-Host ""
Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor "Gray"
Write-Host ""
Write-Host "========================================" -ForegroundColor "Cyan"
Write-Host ""

# Get initial file size
$lastSize = (Get-Item $LogPath).Length
$lastPosition = $lastSize

# Read existing content if file is large (show last 50 lines)
try {
    $fileContent = Get-Content $LogPath -Tail 50 -ErrorAction SilentlyContinue
    if ($fileContent) {
        foreach ($line in $fileContent) {
            if ($line -match $Filter) {
                Write-LogLine $line
            }
        }
        Write-Host ""
        Write-Host "--- Starting real-time monitoring ---" -ForegroundColor "Green"
        Write-Host ""
    }
} catch {
    Write-Host "Starting fresh monitoring..." -ForegroundColor "Yellow"
    Write-Host ""
}

# Monitor file for changes
try {
    $fileStream = [System.IO.File]::Open($LogPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    $reader = New-Object System.IO.StreamReader($fileStream)
    
    # Seek to end of file
    $reader.BaseStream.Seek($lastPosition, [System.IO.SeekOrigin]::Begin) | Out-Null
    
    while ($true) {
        $line = $reader.ReadLine()
        
        if ($null -ne $line) {
            # Apply filter
            if ($line -match $Filter) {
                Write-LogLine $line
            }
        } else {
            # No new line, wait a bit
            Start-Sleep -Milliseconds 500
            
            # Check if file was rotated (size decreased)
            $currentSize = (Get-Item $LogPath).Length
            if ($currentSize -lt $lastSize) {
                Write-Host ""
                Write-Host "⚠️  Log file rotated, reopening..." -ForegroundColor "Yellow"
                Write-Host ""
                $reader.Close()
                $fileStream.Close()
                
                # Reopen file
                $fileStream = [System.IO.File]::Open($LogPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
                $reader = New-Object System.IO.StreamReader($fileStream)
                $lastSize = $currentSize
            } else {
                $lastSize = $currentSize
            }
        }
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error monitoring log file: $_" -ForegroundColor "Red"
    Write-Host ""
} finally {
    if ($reader) { $reader.Close() }
    if ($fileStream) { $fileStream.Close() }
}

