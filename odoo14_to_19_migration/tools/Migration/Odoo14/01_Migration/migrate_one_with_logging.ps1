# PowerShell script for Migration Cron with Logging
# Processes one quotation and logs the result

# Configuration - Change these if needed
$ODOO_URL = "http://localhost:8079"
$ENDPOINT = "/migration/process_one"
$DATABASE = "metrodb"  # Change this to your database name
$LOG_FILE = "C:\logs\migration.log"

# Create log directory if it doesn't exist
if (-not (Test-Path "C:\logs")) {
    New-Item -ItemType Directory -Path "C:\logs" -Force | Out-Null
}

# Get timestamp
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Call the migration endpoint and log output
try {
    $fullUrl = "$ODOO_URL$ENDPOINT" + "?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $fullUrl -UseBasicParsing
    $content = $response.Content
    
    # Log to file
    Add-Content -Path $LOG_FILE -Value "[$TIMESTAMP] Processing migration..."
    Add-Content -Path $LOG_FILE -Value $content
    Add-Content -Path $LOG_FILE -Value ""
    
    # Also show in console
    Write-Host $content
} catch {
    $errorMsg = "ERROR: $_"
    Add-Content -Path $LOG_FILE -Value "[$TIMESTAMP] $errorMsg"
    Write-Host $errorMsg
    exit 1
}
