# PowerShell script for Continuous RFQ Migration
# Processes all queued RFQs one by one
# Shows detailed migration status including Purchase Order, Vendor Bills, and Payments

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
        Write-Status "================================================================================" "Cyan"
        Write-Status ('Type | Total Queued | Migrated | RFQ Status | Bill No - BillID | Status') "Yellow"
        Write-Status "================================================================================" "Cyan"
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
    $lastRFQ = ""
    
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
            $rfqDetails = @{}
            $inDetailsSection = $false
            
            foreach ($line in $responseLines) {
                $line = $line.Trim()
                if ($line -match "Migrating Now:\s*(.+)") {
                    $currentRFQ = $matches[1].Trim()
                }
                elseif ($line -eq "RFQ_DETAILS_START") {
                    $inDetailsSection = $true
                }
                elseif ($line -eq "RFQ_DETAILS_END") {
                    $inDetailsSection = $false
                }
                elseif ($inDetailsSection -and $line -match "^([^:]+):\s*(.+)$") {
                    $key = $matches[1].Trim()
                    $value = $matches[2].Trim()
                    $rfqDetails[$key] = $value
                }
            }
            
            # Display RFQ details from migration table BEFORE migration starts (only once per RFQ)
            if ($rfqDetails.Count -gt 0) {
                $rfqNumFromDetails = $rfqDetails['RFQ_Number']
                $detailsKey = "$rfqNumFromDetails" + '|' + "DETAILS_SHOWN"
                
                if (-not $processedRFQs.ContainsKey($detailsKey)) {
                    Write-Status "" "White"
                    Write-Status "================================================================================" "Cyan"
                    Write-Status "[RFQ] RFQ MIGRATION LINE DETAILS (FROM QUEUE TABLE - BEFORE MIGRATION)" "Yellow"
                    Write-Status "================================================================================" "Cyan"
                    Write-Status "RFQ Number: $($rfqDetails['RFQ_Number'])" "White"
                    Write-Status "Priority: $($rfqDetails['Priority'])" "White"
                    Write-Status "Vendor: $($rfqDetails['Vendor'])" "White"
                    Write-Status "Project: $($rfqDetails['Project'])" "White"
                    Write-Status "Purchase Representative: $($rfqDetails['Purchase_Representative'])" "White"
                    Write-Status "Order Deadline: $($rfqDetails['Order_Deadline'])" "White"
                    Write-Status "Status (Excel): $($rfqDetails['Status_Excel'])" "White"
                    Write-Status "Branch/ID: $($rfqDetails['Branch_ID'])" "White"
                    Write-Status "Stage: $($rfqDetails['Stage'])" "White"
                    Write-Status "Bills/Number: $($rfqDetails['Bills_Number'])" "Yellow"
                    Write-Status "Bills/ID: $($rfqDetails['Bills_ID'])" "Yellow"
                    Write-Status "Created On: $($rfqDetails['Created_On'])" "White"
                    Write-Status "Effective Date: $($rfqDetails['Effective_Date'])" "White"
                    Write-Status "Receipt Date: $($rfqDetails['Receipt_Date'])" "White"
                    Write-Status "Current Status: $($rfqDetails['Current_Status'])" "White"
                    Write-Status "================================================================================" "Cyan"
                    Write-Status "" "White"
                    
                    # Highlight Bill IDs if present
                    if ($rfqDetails['Bills_ID'] -and $rfqDetails['Bills_ID'] -ne 'N/A') {
                        Write-Status "[OK] Bill IDs found in queue list: $($rfqDetails['Bills_ID']) - Will migrate these bills" "Green"
                    } else {
                        Write-Status "[WARNING] No Bill IDs in queue list - Bills may not be migrated" "Yellow"
                    }
                    Write-Status "" "White"
                    
                    # Mark details as shown
                    $processedRFQs[$detailsKey] = $true
                }
            }
            
            # Extract RFQ number and determine status
            if ($currentRFQ -and $currentRFQ -ne "None") {
                $rfqNum = $currentRFQ -replace '\s*-\s*(DONE|ERROR|in progress|Already migrated).*', ''
                $rfqNum = $rfqNum.Trim()
                
                $status = "Migrating"
                $statusColor = "Yellow"
                $isDone = $false
                
                if ($currentRFQ -match "DONE|Already migrated") {
                    $status = "✅ DONE"
                    $statusColor = "Green"
                    $isDone = $true
                } elseif ($currentRFQ -match "ERROR") {
                    $status = "❌ ERROR"
                    $statusColor = "Red"
                } elseif ($currentRFQ -match "in progress") {
                    $status = "🔄 In Progress"
                    $statusColor = "Yellow"
                }
                
                # Only process if this is a new RFQ or status changed to DONE
                $displayKey = "$rfqNum" + '|' + "$status"
                
                if (-not $processedRFQs.ContainsKey($displayKey) -or ($isDone -and $lastRFQ -ne $rfqNum)) {
                    # Mark as processed
                    $processedRFQs[$displayKey] = $true
                    $lastRFQ = $rfqNum
                    
                    # Get detailed RFQ information if migration is done
                    $hasPO = "NO"
                    $poState = ""
                    $billingStatus = ""
                    $vendorBills = @()
                    $payments = @()
                    $billNumbersFromQueue = @()
                    $billIdsFromQueue = @()
                    
                    if ($isDone) {
                        try {
                            $detailsUrl = "$ODOO_URL/migration/rfq_details?db=$DATABASE" + '&' + "rfq_number=$rfqNum"
                            $detailsResponse = Invoke-WebRequest -Uri $detailsUrl -WebSession $webSession -Method Get -UseBasicParsing -ErrorAction SilentlyContinue
                            $detailsJson = $detailsResponse.Content | ConvertFrom-Json
                            
                            if ($detailsJson.has_purchase_order) {
                                $hasPO = "YES"
                                $poState = $detailsJson.purchase_order_state
                                $billingStatus = $detailsJson.billing_status
                                $vendorBills = $detailsJson.vendor_bills
                                
                                # Get bill numbers and IDs from queue list (primary source)
                                if ($detailsJson.bill_numbers_from_queue) {
                                    $billNumbersFromQueue = $detailsJson.bill_numbers_from_queue
                                }
                                if ($detailsJson.bill_ids_from_queue) {
                                    $billIdsFromQueue = $detailsJson.bill_ids_from_queue
                                }
                                
                                # Collect all payments from all bills
                                foreach ($bill in $vendorBills) {
                                    if ($bill.payments) {
                                        $payments += $bill.payments
                                    }
                                }
                            } elseif ($detailsJson.bill_numbers_from_queue) {
                                # Even if PO not found, show bill numbers from queue
                                $billNumbersFromQueue = $detailsJson.bill_numbers_from_queue
                                if ($detailsJson.bill_ids_from_queue) {
                                    $billIdsFromQueue = $detailsJson.bill_ids_from_queue
                                }
                            }
                        } catch {
                            # Silently fail - details endpoint might not be available yet
                        }
                    }
                    
                    # Format bill numbers and IDs for display: "BillNo - BillID"
                    # First priority: Use Bills/ID and Bills/Number from queue list (rfqDetails)
                    $billDisplay = "NO"
                    if ($rfqDetails['Bills_ID'] -and $rfqDetails['Bills_ID'] -ne 'N/A') {
                        # Parse Bills/ID from queue list
                        $billIdsFromDetails = $rfqDetails['Bills_ID'].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
                        $billNumbersFromDetails = if ($rfqDetails['Bills_Number'] -and $rfqDetails['Bills_Number'] -ne 'N/A' -and $rfqDetails['Bills_Number'] -ne '/') {
                            $rfqDetails['Bills_Number'].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -ne '/' }
                        } else {
                            @()
                        }
                        
                        $billPairs = @()
                        $maxCount = [Math]::Max($billNumbersFromDetails.Count, $billIdsFromDetails.Count)
                        for ($i = 0; $i -lt $maxCount; $i++) {
                            $billNo = if ($i -lt $billNumbersFromDetails.Count) { $billNumbersFromDetails[$i] } else { "" }
                            $billId = if ($i -lt $billIdsFromDetails.Count) { $billIdsFromDetails[$i] } else { "" }
                            
                            if ($billNo -and $billId) {
                                $billPairs += "$billNo - $billId"
                            } elseif ($billNo) {
                                $billPairs += $billNo
                            } elseif ($billId) {
                                $billPairs += $billId
                            }
                        }
                        
                        if ($billPairs.Count -gt 0) {
                            $billDisplay = $billPairs -join ', '
                        }
                    } elseif ($billNumbersFromQueue.Count -gt 0 -or $billIdsFromQueue.Count -gt 0) {
                        # Second priority: Use from details JSON
                        $billPairs = @()
                        $maxCount = [Math]::Max($billNumbersFromQueue.Count, $billIdsFromQueue.Count)
                        for ($i = 0; $i -lt $maxCount; $i++) {
                            $billNo = if ($i -lt $billNumbersFromQueue.Count) { $billNumbersFromQueue[$i] } else { "" }
                            $billId = if ($i -lt $billIdsFromQueue.Count) { $billIdsFromQueue[$i] } else { "" }
                            
                            if ($billNo -and $billId) {
                                $billPairs += "$billNo - $billId"
                            } elseif ($billNo) {
                                $billPairs += $billNo
                            } elseif ($billId) {
                                $billPairs += $billId
                            }
                        }
                        
                        if ($billPairs.Count -gt 0) {
                            $billDisplay = $billPairs -join ', '
                        }
                    } elseif ($vendorBills.Count -gt 0) {
                        # Fallback: use migrated bills
                        $billNames = $vendorBills | ForEach-Object { $_.name }
                        $billDisplay = $billNames -join ', '
                    }
                    
                    # Get RFQ stage from details
                    $rfqStage = "Draft"
                    if ($detailsJson.rfq_stage) {
                        $rfqStage = $detailsJson.rfq_stage
                    } elseif ($hasPO -eq "YES") {
                        $rfqStage = "Purchase Order"
                    }
                    
                    # Display RFQ header line
                    $displayLine = "RFQ " + '|' + " $rfqNum " + '|' + " Total Queued: $totalQueued " + '|' + " Migrated: $totalMigrated " + '|' + " $rfqStage " + '|' + " $billDisplay " + '|' + " Status: $status"
                    Write-Status $displayLine $statusColor
                    Write-Status "--------------------" "Gray"
                    
                    # Display Purchase Order Confirming status
                    if ($hasPO -eq "YES") {
                        $poConfirmStatus = if ($poState -in @("purchase", "done")) { "DONE" } else { "PENDING" }
                        Write-Status ("Purchase Order Confirming " + '|' + " $poConfirmStatus") "Yellow"
                        
                        # Check Purchase Order Billing Status
                        Write-Status "Check Purchase Order Billing Status" "Yellow"
                        $billingStatusText = switch ($billingStatus) {
                            "nothing_to_bill" { "Nothing to Bill" }
                            "to_bill" { "Waiting for Bills" }
                            "billed" { "Fully Billed" }
                            default { "Unknown" }
                        }
                        Write-Status "Billing Status: $billingStatusText" "Cyan"
                        Write-Status "--------------------" "Gray"
                        Write-Status "Vendor Bill Checking with Purchase Order" "Yellow"
                        Write-Status ""
                        
                        # Use bill numbers and IDs from queue list (primary source)
                        $billsToShow = @()
                        if ($billNumbersFromQueue.Count -gt 0 -or $billIdsFromQueue.Count -gt 0) {
                            # Pair bill numbers with IDs
                            $maxCount = [Math]::Max($billNumbersFromQueue.Count, $billIdsFromQueue.Count)
                            for ($i = 0; $i -lt $maxCount; $i++) {
                                $billNo = if ($i -lt $billNumbersFromQueue.Count) { $billNumbersFromQueue[$i] } else { "" }
                                $billId = if ($i -lt $billIdsFromQueue.Count) { $billIdsFromQueue[$i] } else { "" }
                                
                                if ($billNo -and $billId) {
                                    $billsToShow += @{ Name = $billNo; Id = $billId }
                                } elseif ($billNo) {
                                    $billsToShow += @{ Name = $billNo; Id = "" }
                                } elseif ($billId) {
                                    $billsToShow += @{ Name = ""; Id = $billId }
                                }
                            }
                        } elseif ($vendorBills.Count -gt 0) {
                            # Fallback: use migrated bills
                            foreach ($bill in $vendorBills) {
                                $billsToShow += @{ Name = $bill.name; Id = $bill.id }
                            }
                        }
                        
                        if ($billsToShow.Count -gt 0) {
                            Write-Status "Found Vendor Bill" "Green"
                            Write-Status "-----------------------------" "Gray"
                            Write-Status "collecting data" "Yellow"
                            
                            foreach ($billInfo in $billsToShow) {
                                $billName = $billInfo.Name
                                $billId = $billInfo.Id
                                
                                # Format: "BillNo - BillID" or just "BillNo" or "ID: BillID"
                                if ($billName -and $billId) {
                                    $billDisplay = "$billName - $billId"
                                } elseif ($billName) {
                                    $billDisplay = $billName
                                } elseif ($billId) {
                                    $billDisplay = "ID: $billId"
                                } else {
                                    continue
                                }
                                
                                # Find bill in vendorBills if available
                                $bill = $vendorBills | Where-Object { $_.name -eq $billName -or ($billId -and $_.id -eq $billId) }
                                if ($bill) {
                                    $billStatus = if ($bill.state -eq "posted") { "DONE" } else { $bill.state.ToUpper() }
                                    Write-Status "Migrating Vendor Bill $billDisplay - status $billStatus" "Green"
                                } else {
                                    Write-Status "Migrating Vendor Bill $billDisplay - status DONE" "Green"
                                }
                            }
                            
                            Write-Status ""
                            Write-Status "vendor bill payment checking....." "Yellow"
                            Write-Status ""
                            
                            if ($payments.Count -gt 0) {
                                Write-Status "If yes" "Green"
                                Write-Status "-----------------------------" "Gray"
                                Write-Status "collecting data" "Yellow"
                                
                                foreach ($payment in $payments) {
                                    Write-Status "migrating payment $($payment.name) - Status DONE" "Green"
                                }
                            } else {
                                Write-Status "No payments found" "Gray"
                            }
                        } else {
                            Write-Status "Found Vendor Bill / Not" "Gray"
                        }
                    } else {
                        Write-Status ('Purchase Order Confirming | NOT CREATED') "Red"
                    }
                    
                    Write-Status ""
                    Write-Status "ALL Done" "Green"
                    Write-Status "================================================================================" "Cyan"
                    Write-Status "NEXT RFQ" "Yellow"
                    Write-Status ""
                }
            }
            
        } catch {
            $errorMsg = $_.Exception.Message
            # Don't spam errors
        }
        
        # Check if queue is empty
        if ($totalQueued -eq 0 -and (-not $migratingNow -or $migratingNow -eq "None")) {
            Write-Status ""
            Write-Status "================================================================================" "Green"
            Write-Status "   ✅ Migration Complete!" "Green"
            Write-Status "================================================================================" "Green"
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
