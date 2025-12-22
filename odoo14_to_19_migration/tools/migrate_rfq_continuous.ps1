# PowerShell script for Continuous RFQ Migration
# Processes all queued RFQs one by one
# Shows each RFQ on a line: RFQ | Total Queued | Migrated | Current Migration | Status
# List persists and grows as RFQs are processed

# Configuration - Change these if needed
$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"  # Change this to your database name
$PROCESSING_DELAY = 2  # Seconds to wait between processing each RFQ

# Colors for output
function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Track processed RFQs to avoid duplicates
$processedRFQs = @{}

try {
    Write-Status ""
    Write-Status "=== RFQ Migration Processor ===" "Cyan"
    Write-Status ""
    Write-Status "Configuration:" "Yellow"
    Write-Status "  Database: $DATABASE" "Gray"
    Write-Status "  URL: $ODOO_URL" "Gray"
    Write-Status "  Processing Delay: $PROCESSING_DELAY seconds" "Gray"
    Write-Status ""
    
    # Step 1: Establish database session
    Write-Status "Establishing database session..." "Yellow"
    try {
        $null = Invoke-WebRequest -Uri "$ODOO_URL/web?db=$DATABASE" -SessionVariable webSession -UseBasicParsing -ErrorAction Stop
        Write-Status "  ✅ Session established" "Green"
    } catch {
        Write-Status "  ❌ Failed to establish session: $_" "Red"
        Write-Status "     Please ensure Odoo is running and database '$DATABASE' exists" "Gray"
        exit 1
    }
    Write-Status ""
    
    # Get initial status
    $statusUrl = "$ODOO_URL/migration/status_rfq?db=$DATABASE"
    $processUrl = "$ODOO_URL/migration/process_one_rfq?db=$DATABASE"
    
    try {
        $statusResponse = Invoke-WebRequest -Uri $statusUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
        $statusJson = $statusResponse.Content | ConvertFrom-Json
        
        $totalQueued = $statusJson.total_queued
        $totalMigrated = $statusJson.total_migrated
        $totalErrors = $statusJson.total_errors
        
        Write-Status "  ✅ Initial status retrieved" "Green"
        Write-Status ""
        
        if ($totalQueued -eq 0) {
            Write-Status "✅ No RFQs in queue. Nothing to process." "Green"
            Write-Status ""
            exit 0
        }
        
        Write-Status "Starting migration process..." "Yellow"
        Write-Status "Press Ctrl+C to stop at any time" "Gray"
        Write-Status ""
        Write-Status "========================================" "Cyan"
        Write-Status "RFQ | Total Queued | Migrated | Current Migration | Status" "Yellow"
        Write-Status "========================================" "Cyan"
        Write-Status ""
        Start-Sleep -Seconds 2
        
    } catch {
        $errorMsg = $_.Exception.Message
        $statusCode = $_.Exception.Response.StatusCode.value__
        
        if ($statusCode -eq 404) {
            Write-Status "  ❌ Route not found (404)" "Red"
            Write-Status "     Please upgrade the module: Apps > odoo14_to_19_migration > Upgrade" "Yellow"
            Write-Status "     Then FULLY restart Odoo server" "Yellow"
        } else {
            Write-Status "  ❌ Error getting status: $errorMsg" "Red"
        }
        exit 1
    }
    
    # Process loop - continue until queue is 0
    $iteration = 0
    
    while ($true) {
        $iteration++
        
        # Get current status
        try {
            $statusResponse = Invoke-WebRequest -Uri $statusUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
            $statusJson = $statusResponse.Content | ConvertFrom-Json
            $totalQueued = $statusJson.total_queued
            $migratingNow = $statusJson.migrating_now
            $totalMigrated = $statusJson.total_migrated
            $totalErrors = $statusJson.total_errors
        } catch {
            Write-Status "  ⚠️  Error getting status: $($_.Exception.Message)" "Yellow"
            Start-Sleep -Seconds $PROCESSING_DELAY
            continue
        }
        
        # Process one RFQ
        try {
            $processResponse = Invoke-WebRequest -Uri $processUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
            $responseLines = $processResponse.Content -split "`n"
            
            $currentRFQ = "None"
            foreach ($line in $responseLines) {
                $line = $line.Trim()
                if ($line -match "Migrating Now:\s*(.+)") {
                    $currentRFQ = $matches[1].Trim()
                }
            }
            
            # Extract RFQ number and determine status
            if ($currentRFQ -and $currentRFQ -ne "None") {
                $rfqNum = $currentRFQ -replace '\s*-\s*(DONE|ERROR|in progress|Already migrated).*', ''
                $rfqNum = $rfqNum.Trim()
                
                $status = "Migrating"
                $statusColor = "Yellow"
                if ($currentRFQ -match "DONE|Already migrated") {
                    $status = "✅ DONE"
                    $statusColor = "Green"
                } elseif ($currentRFQ -match "ERROR") {
                    $status = "❌ ERROR"
                    $statusColor = "Red"
                } elseif ($currentRFQ -match "in progress") {
                    $status = "🔄 In Progress"
                    $statusColor = "Yellow"
                }
                
                # Create unique key for this RFQ+status combination
                $displayKey = "$rfqNum|$status"
                
                # Only display if this is a new RFQ or status changed
                if (-not $processedRFQs.ContainsKey($displayKey)) {
                    # Mark as processed
                    $processedRFQs[$displayKey] = $true
                    
                    # Display the line with all info
                    $displayLine = "$rfqNum | Total Queued: $totalQueued | Migrated: $totalMigrated | Current: $currentRFQ | Status: $status"
                    Write-Status $displayLine $statusColor
                }
            }
            
        } catch {
            $errorMsg = $_.Exception.Message
            # Don't spam errors
        }
        
        # Check if queue is empty
        if ($totalQueued -eq 0 -and (-not $migratingNow -or $migratingNow -eq "None")) {
            Write-Status ""
            Write-Status "========================================" "Green"
            Write-Status "   ✅ Migration Complete!" "Green"
            Write-Status "========================================" "Green"
            Write-Status ""
            Write-Status "Final Summary:" "Yellow"
            Write-Status "  Total Migrated: $totalMigrated" "Green"
            Write-Status "  Total Errors: $totalErrors" "Red"
            Write-Status ""
            break
        }
        
        # Wait before next iteration
        Start-Sleep -Seconds $PROCESSING_DELAY
    }
    
} catch {
    Write-Status ""
    Write-Status "ERROR: $_" "Red"
    Write-Status ""
    Write-Status "Troubleshooting:" "Yellow"
    Write-Status "  1. Ensure Odoo server is running on $ODOO_URL" "Gray"
    Write-Status "  2. Verify database name '$DATABASE' is correct" "Gray"
    Write-Status "  3. Check that migration routes are accessible" "Gray"
    Write-Status ""
    exit 1
}

