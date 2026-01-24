# PowerShell script for Migration Cron
# Processes quotations from the queue until empty

# Configuration - Change these if needed
$ODOO_URL = "http://localhost:8079"
$ENDPOINT = "/migration/process_one"
$DATABASE = "metrodb"  # Change this to your database name

# SOLUTION: Get web session first to establish database context
# Odoo 19 requires database selection before routing, even with auth='none'
try {
    # Step 1: Access web interface to create session with database
    Write-Host "Establishing database session..." -ForegroundColor Gray
    $null = Invoke-WebRequest -Uri "$ODOO_URL/web?db=$DATABASE" -SessionVariable webSession -UseBasicParsing -ErrorAction Stop
    
    # Step 2: Loop until queue is empty
    $maxIterations = 200  # Safety limit (reduced from 1000)
    $iteration = 0
    $previousMigrating = ""
    $stuckCount = 0
    
    Write-Host ""
    Write-Host "=== Starting Migration Process ===" -ForegroundColor Cyan
    Write-Host ""
    
    while ($iteration -lt $maxIterations) {
        $iteration++
        
        # Call migration route
        $fullUrl = "$ODOO_URL$ENDPOINT" + "?db=$DATABASE"
        $response = Invoke-WebRequest -Uri $fullUrl -WebSession $webSession -UseBasicParsing
        $content = $response.Content
        
        # Parse response
        $lines = $content -split "`n"
        $totalQueued = 0
        $migratingNow = "None"
        
        foreach ($line in $lines) {
            if ($line -match "Total Queued:\s*(\d+)") {
                $totalQueued = [int]$matches[1]
            }
            if ($line -match "Migrating Now:\s*(.+)") {
                $migratingNow = $matches[1].Trim()
            }
        }
        
        # Display status
        Write-Host "[$iteration] Total Queued: $totalQueued | Migrating: $migratingNow" -ForegroundColor Yellow
        
        # Check if done
        if ($totalQueued -eq 0 -and $migratingNow -eq "None") {
            Write-Host ""
            Write-Host "✅ All quotations processed! Queue is empty." -ForegroundColor Green
            break
        }
        
        # If still processing the same quotation, wait longer
        if ($migratingNow -ne "None" -and $migratingNow -notmatch "DONE|ERROR|in progress") {
            # If it shows DONE or ERROR, it completed, continue immediately
            Start-Sleep -Milliseconds 500  # Brief pause
        } elseif ($migratingNow -match "in progress") {
            # If it's in progress, wait a bit longer
            Start-Sleep -Seconds 3
        } else {
            Start-Sleep -Milliseconds 500  # Brief pause between migrations
        }
        
        # Safety check: if same quotation is being processed for too long, break
        if ($iteration -gt 5 -and $migratingNow -eq $previousMigrating -and $migratingNow -notmatch "DONE|ERROR") {
            Write-Host ""
            Write-Host "⚠️  Same quotation stuck: $migratingNow" -ForegroundColor Yellow
            Write-Host "   Breaking loop to prevent infinite retry" -ForegroundColor Yellow
            break
        }
        
        $previousMigrating = $migratingNow
    }
    
    if ($iteration -ge $maxIterations) {
        Write-Host ""
        Write-Host "⚠️  Reached maximum iterations ($maxIterations). Stopping." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "=== Migration Process Complete ===" -ForegroundColor Cyan
    
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    exit 1
}
