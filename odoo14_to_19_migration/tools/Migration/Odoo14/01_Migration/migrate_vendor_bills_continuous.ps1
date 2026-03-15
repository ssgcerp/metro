# PowerShell script for Continuous Vendor Bill Migration
# Processes all queued vendor bills one by one
# Shows each bill on a line: Bill | Total Queued | Migrated | Current Migration | Status
# List persists and grows as bills are processed

# Configuration - Change these if needed
$ODOO_URL = "https://metro.equdaierp.com"
$DATABASE = "newdb"  # Change this to your database name
$PROCESSING_DELAY = 2  # Seconds to wait between processing each bill

# Colors for output
function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Track processed bills to avoid duplicates
$processedBills = @{}

try {
    Write-Status ""
    Write-Status "=== Vendor Bill Migration Processor ===" "Cyan"
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
    }
    catch {
        Write-Status "  ❌ Failed to establish session: $_" "Red"
        Write-Status "     Please ensure Odoo is running and database '$DATABASE' exists" "Gray"
        exit 1
    }
    Write-Status ""
    
    # Get initial status
    $statusUrl = "$ODOO_URL/migration/status_vendor_bill?db=$DATABASE"
    $processUrl = "$ODOO_URL/migration/process_one_vendor_bill?db=$DATABASE"
    
    try {
        $statusResponse = Invoke-WebRequest -Uri $statusUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
        $statusJson = $statusResponse.Content | ConvertFrom-Json
        
        $totalQueued = $statusJson.total_queued
        $totalMigrated = $statusJson.total_migrated
        $totalErrors = $statusJson.total_errors
        
        Write-Status "  ✅ Initial status retrieved" "Green"
        Write-Status ""
        
        if ($totalQueued -eq 0) {
            Write-Status "✅ No vendor bills in queue. Nothing to process." "Green"
            Write-Status ""
            exit 0
        }
        
        Write-Status "Starting migration process..." "Yellow"
        Write-Status "Press Ctrl+C to stop at any time" "Gray"
        Write-Status ""
        Write-Status "========================================" "Cyan"
        Write-Status "Bill | Total Queued | Migrated | Odoo 14 Products | Odoo 19 Products | Current Migration | Status" "Yellow"
        Write-Status "========================================" "Cyan"
        Write-Status ""
        Start-Sleep -Seconds 2
        
    }
    catch {
        $errorMsg = $_.Exception.Message
        $statusCode = $_.Exception.Response.StatusCode.value__
        
        if ($statusCode -eq 404) {
            Write-Status "  ❌ Route not found (404)" "Red"
            Write-Status "     Please upgrade the module: Apps > odoo14_to_19_migration > Upgrade" "Yellow"
            Write-Status "     Then FULLY restart Odoo server" "Yellow"
        }
        else {
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
        }
        catch {
            Write-Status "  ⚠️  Error getting status: $($_.Exception.Message)" "Yellow"
            Start-Sleep -Seconds $PROCESSING_DELAY
            continue
        }
        
        # Process one vendor bill
        try {
            $processResponse = Invoke-WebRequest -Uri $processUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction Stop
            $responseLines = $processResponse.Content -split "`n"
            
            $currentBill = "None"
            $billDetails = @{
                'bill_number'          = ''
                'vendor'               = ''
                'amount'               = 0.0
                'payments'             = 0
                'total_items_odoo14'   = 0
                'total_items_migrated' = 0
                'products_odoo14'      = 0
                'products_odoo19'      = 0
            }
            $inDetailsSection = $false
            
            foreach ($line in $responseLines) {
                $line = $line.Trim()
                
                if ($line -match "Migrating Now:\s*(.+)") {
                    $currentBill = $matches[1].Trim()
                }
                
                # Parse bill details section
                if ($line -match "Migrating Vendor Bill details:") {
                    $inDetailsSection = $true
                }
                elseif ($inDetailsSection) {
                    if ($line -match "Bill Number:\s*(.+)") {
                        $billDetails['bill_number'] = $matches[1].Trim()
                    }
                    elseif ($line -match "Vendor:\s*(.+)") {
                        $billDetails['vendor'] = $matches[1].Trim()
                    }
                    elseif ($line -match "Total Bill Amount:\s*([0-9,]+\.?[0-9]*)") {
                        $amountStr = $matches[1] -replace ',', ''
                        $billDetails['amount'] = [double]$amountStr
                    }
                    elseif ($line -match "Payments Linked:\s*(\d+)") {
                        $billDetails['payments'] = [int]$matches[1]
                    }
                    elseif ($line -match "Total Items \(Odoo 14\):\s*(\d+)") {
                        $billDetails['total_items_odoo14'] = [int]$matches[1]
                    }
                    elseif ($line -match "Total Items Migrated:\s*(\d+)") {
                        $billDetails['total_items_migrated'] = [int]$matches[1]
                    }
                    elseif ($line -match "Products \(Odoo 14\):\s*(\d+)") {
                        $billDetails['products_odoo14'] = [int]$matches[1]
                    }
                    elseif ($line -match "Products Migrated:\s*(\d+)") {
                        $billDetails['products_odoo19'] = [int]$matches[1]
                    }
                    elseif ($line -eq "" -or $line -match "Total Queued:") {
                        $inDetailsSection = $false
                    }
                }
            }
            
            # Extract bill number and determine status
            if ($currentBill -and $currentBill -ne "None") {
                $billNum = $currentBill -replace '\s*-\s*(DONE|ERROR|in progress|Already migrated).*', ''
                $billNum = $billNum.Trim()
                
                # Use bill number from details if available
                if ($billDetails['bill_number'] -and $billDetails['bill_number'] -ne 'N/A') {
                    $billNum = $billDetails['bill_number']
                }
                
                $status = "Migrating"
                $statusColor = "Yellow"
                if ($currentBill -match "DONE|Already migrated") {
                    $status = "✅ DONE"
                    $statusColor = "Green"
                }
                elseif ($currentBill -match "ERROR") {
                    $status = "❌ ERROR"
                    $statusColor = "Red"
                }
                elseif ($currentBill -match "in progress") {
                    $status = "🔄 In Progress"
                    $statusColor = "Yellow"
                }
                
                # Create unique key for this bill+status combination
                $displayKey = "$billNum|$status"
                
                # Only display if this is a new bill or status changed
                if (-not $processedBills.ContainsKey($displayKey)) {
                    # Mark as processed
                    $processedBills[$displayKey] = $true
                    
                    # Display bill details header if available
                    if ($billDetails['bill_number'] -and $billDetails['bill_number'] -ne 'N/A' -and $billDetails['bill_number'] -ne '') {
                        Write-Status ""
                        Write-Status "Migrating Vendor Bill details" "Cyan"
                        Write-Status "Bill Number: $($billDetails['bill_number'])" "Gray"
                        if ($billDetails['vendor'] -and $billDetails['vendor'] -ne 'N/A') {
                            Write-Status "Vendor: $($billDetails['vendor'])" "Gray"
                        }
                        if ($billDetails['amount'] -gt 0) {
                            Write-Status "Total Bill Amount: $($billDetails['amount'].ToString('N2'))" "Gray"
                        }
                        if ($billDetails['total_items_odoo14'] -gt 0) {
                            Write-Status "Total Items: $($billDetails['total_items_odoo14'])" "Cyan"
                        }
                        if ($billDetails['total_items_migrated'] -gt 0) {
                            Write-Status "Total Items Migrated: $($billDetails['total_items_migrated'])" "Green"
                        }
                        if ($billDetails['payments'] -gt 0) {
                            Write-Status "Payments Linked: $($billDetails['payments'])" "Green"
                        }
                        Write-Status ""
                    }
                    
                    # Display the line with all info
                    $products14 = if ($billDetails['products_odoo14'] -gt 0) { $billDetails['products_odoo14'] } else { "N/A" }
                    $products19 = if ($billDetails['products_odoo19'] -gt 0) { $billDetails['products_odoo19'] } else { "N/A" }
                    $displayLine = "$billNum | Total Queued: $totalQueued | Migrated: $totalMigrated | Odoo 14 Products: $products14 | Odoo 19 Products: $products19 | Current: $currentBill | Status: $status"
                    Write-Status $displayLine $statusColor
                }
            }
            
        }
        catch {
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
    
}
catch {
    Write-Status ""
    Write-Status "ERROR: $_" "Red"
    Write-Status ""
    Write-Status "Troubleshooting:" "Yellow"
    Write-Status "  1. Ensure Odoo server is running on $ODOO_URL" "Gray"
    Write-Status "  2. Verify database name '$DATABASE' is correct" "Gray"
    Write-Status "  3. Check that migration routes are accessible" "Gray"
    Write-Status "  4. Ensure vendor bill endpoints are available:" "Gray"
    Write-Status "     - /migration/status_vendor_bill" "Gray"
    Write-Status "     - /migration/process_one_vendor_bill" "Gray"
    Write-Status ""
    exit 1
}

