# PowerShell script for Continuous Customer Invoice Migration
# Processes all queued invoices one by one
# Shows each invoice on a line: Invoice | Total Queued | Migrated | Current Migration | Status
# List persists and grows as invoices are processed

# Configuration - Change these if needed
$ODOO_URL = "http://localhost:8079"
$DATABASE = "metrodb"  # Change this to your database name
$PROCESSING_DELAY = 2  # Seconds to wait between processing each invoice

# Colors for output
function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Track processed invoices to avoid duplicates
$processedInvoices = @{}

try {
    Write-Status ""
    Write-Status "=== Customer Invoice Migration Processor ===" "Cyan"
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
    $statusUrl = "$ODOO_URL/migration/status_invoice?db=$DATABASE"
    $processUrl = "$ODOO_URL/migration/process_one_invoice?db=$DATABASE"
    
    try {
        $statusResponse = Invoke-WebRequest -Uri $statusUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
        $statusJson = $statusResponse.Content | ConvertFrom-Json
        
        $totalQueued = $statusJson.total_queued
        $totalMigrated = $statusJson.total_migrated
        $totalErrors = $statusJson.total_errors
        
        Write-Status "  ✅ Initial status retrieved" "Green"
        Write-Status ""
        
        if ($totalQueued -eq 0) {
            Write-Status "✅ No invoices in queue. Nothing to process." "Green"
            Write-Status ""
            exit 0
        }
        
        Write-Status "Starting migration process..." "Yellow"
        Write-Status "Press Ctrl+C to stop at any time" "Gray"
        Write-Status ""
        Write-Status "========================================" "Cyan"
        Write-Status "Invoice | Total Queued | Migrated | Current Migration | Status" "Yellow"
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
        
        # Process one invoice
        try {
            $processResponse = Invoke-WebRequest -Uri $processUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
            $responseLines = $processResponse.Content -split "`n"
            
            $currentInvoice = "None"
            foreach ($line in $responseLines) {
                if ($line -match "Migrating Now:\s*(.+)") {
                    $currentInvoice = $matches[1].Trim()
                }
            }
            
            # Extract invoice number and determine status
            if ($currentInvoice -and $currentInvoice -ne "None") {
                $invoiceNum = $currentInvoice -replace '\s*-\s*(DONE|ERROR|in progress|Already migrated).*', ''
                $invoiceNum = $invoiceNum.Trim()
                
                $status = "Migrating"
                $statusColor = "Yellow"
                if ($currentInvoice -match "DONE|Already migrated") {
                    $status = "✅ DONE"
                    $statusColor = "Green"
                } elseif ($currentInvoice -match "ERROR") {
                    $status = "❌ ERROR"
                    $statusColor = "Red"
                } elseif ($currentInvoice -match "in progress") {
                    $status = "🔄 In Progress"
                    $statusColor = "Yellow"
                }
                
                # Create unique key for this invoice+status combination
                $displayKey = "$invoiceNum|$status"
                
                # Only display if this is a new invoice or status changed
                if (-not $processedInvoices.ContainsKey($displayKey)) {
                    # Mark as processed
                    $processedInvoices[$displayKey] = $true
                    
                    # Display the line with all info
                    $displayLine = "$invoiceNum | Total Queued: $totalQueued | Migrated: $totalMigrated | Current: $currentInvoice | Status: $status"
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

