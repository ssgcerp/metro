# PowerShell script to check migration status
# Shows current migration status without processing

# Configuration - Change these if needed
$ODOO_URL = "http://localhost:8079"
$ENDPOINT = "/migration/status"
$DATABASE = "metrodb"  # Change this to your database name

# SOLUTION: Get web session first to establish database context
try {
    # Step 1: Access web interface to create session with database
    $null = Invoke-WebRequest -Uri "$ODOO_URL/web?db=$DATABASE" -SessionVariable webSession -UseBasicParsing -ErrorAction Stop
    
    # Step 2: Now call status endpoint with the session
    $fullUrl = "$ODOO_URL$ENDPOINT" + "?db=$DATABASE"
    $response = Invoke-WebRequest -Uri $fullUrl -WebSession $webSession -UseBasicParsing
    $json = $response.Content | ConvertFrom-Json
    
    # Pretty print JSON
    $json | ConvertTo-Json -Depth 10
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    exit 1
}
