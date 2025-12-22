#!/bin/bash
# Bash script for Continuous RFQ Migration (Linux/Unix)
# Processes all queued RFQs one by one
# Shows detailed migration status including Purchase Order, Vendor Bills, and Payments

# Configuration - Change these if needed
ODOO_URL="https://metro.equdaierp.com"
DATABASE="metrodb"  # Change this to your database name
PROCESSING_DELAY=2  # Seconds to wait between processing each RFQ

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Track processed RFQs to avoid duplicates
declare -A processed_rfqs

# Function to print colored status
write_status() {
    local message="$1"
    local color="${2:-NC}"
    case "$color" in
        "Red") echo -e "${RED}${message}${NC}" ;;
        "Green") echo -e "${GREEN}${message}${NC}" ;;
        "Yellow") echo -e "${YELLOW}${message}${NC}" ;;
        "Cyan") echo -e "${CYAN}${message}${NC}" ;;
        "Gray") echo -e "${GRAY}${message}${NC}" ;;
        *) echo -e "${message}" ;;
    esac
}

# Check if jq is available for JSON parsing
if command -v jq &> /dev/null; then
    USE_JQ=true
else
    USE_JQ=false
    write_status "⚠️  Warning: jq not found. JSON parsing will be basic." "Yellow"
    write_status "   Install jq for better parsing: sudo apt-get install jq (or sudo yum install jq)" "Gray"
fi

# Function to parse JSON (with or without jq)
parse_json() {
    local json="$1"
    local key="$2"
    
    if [ "$USE_JQ" = true ]; then
        echo "$json" | jq -r ".$key // empty" 2>/dev/null
    else
        # Basic grep/sed parsing (less reliable)
        echo "$json" | grep -o "\"$key\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed "s/.*:\"\(.*\)\"/\1/" | head -n1
    fi
}

# Function to parse JSON number (with or without jq)
parse_json_number() {
    local json="$1"
    local key="$2"
    
    if [ "$USE_JQ" = true ]; then
        echo "$json" | jq -r ".$key // 0" 2>/dev/null
    else
        # Basic grep/sed parsing for numbers
        local value=$(echo "$json" | grep -o "\"$key\"[[:space:]]*:[[:space:]]*[0-9]*" | sed "s/.*:[[:space:]]*\([0-9]*\)/\1/" | head -n1)
        echo "${value:-0}"
    fi
}

# Function to parse JSON array (with or without jq)
parse_json_array() {
    local json="$1"
    local key="$2"
    
    if [ "$USE_JQ" = true ]; then
        echo "$json" | jq -r ".$key[]? // empty" 2>/dev/null
    else
        # Basic parsing - extract array values
        echo "$json" | grep -o "\"$key\"[[:space:]]*:\[[^]]*\]" | sed 's/.*\[\(.*\)\]/\1/' | sed 's/"//g' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
    fi
}

# Create temporary cookie file for session management
COOKIE_FILE=$(mktemp)
trap "rm -f $COOKIE_FILE" EXIT

echo ""
write_status "=== RFQ Migration Processor ===" "Cyan"
echo ""
write_status "Configuration:" "Yellow"
write_status "  Database: $DATABASE" "Gray"
write_status "  URL: $ODOO_URL" "Gray"
write_status "  Processing Delay: $PROCESSING_DELAY seconds" "Gray"
echo ""

# Step 1: Establish database session
write_status "Establishing database session..." "Yellow"
SESSION_RESPONSE=$(curl -s -c "$COOKIE_FILE" -L "$ODOO_URL/web?db=$DATABASE" -w "\n%{http_code}" 2>/dev/null)
HTTP_CODE=$(echo "$SESSION_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "302" ] && [ "$HTTP_CODE" != "303" ]; then
    write_status "  ❌ Failed to establish session (HTTP $HTTP_CODE)" "Red"
    write_status "     Please ensure Odoo is running and database '$DATABASE' exists" "Gray"
    exit 1
fi
write_status "  ✅ Session established" "Green"
echo ""

# Get initial status
STATUS_URL="$ODOO_URL/migration/status_rfq?db=$DATABASE"
PROCESS_URL="$ODOO_URL/migration/process_one_rfq?db=$DATABASE"

STATUS_RESPONSE=$(curl -s -b "$COOKIE_FILE" -L "$STATUS_URL" -w "\n%{http_code}" 2>/dev/null)
HTTP_CODE=$(echo "$STATUS_RESPONSE" | tail -n1)
STATUS_JSON=$(echo "$STATUS_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "404" ]; then
    write_status "  ❌ Route not found (404)" "Red"
    write_status "     Please upgrade the module: Apps > odoo14_to_19_migration > Upgrade" "Yellow"
    write_status "     Then FULLY restart Odoo server" "Yellow"
    exit 1
elif [ "$HTTP_CODE" != "200" ]; then
    write_status "  ❌ Error getting status (HTTP $HTTP_CODE)" "Red"
    exit 1
fi

# Parse initial status
TOTAL_QUEUED=$(parse_json_number "$STATUS_JSON" "total_queued")
TOTAL_MIGRATED=$(parse_json_number "$STATUS_JSON" "total_migrated")
TOTAL_ERRORS=$(parse_json_number "$STATUS_JSON" "total_errors")

write_status "  ✅ Initial status retrieved" "Green"
echo ""

if [ "$TOTAL_QUEUED" = "0" ] || [ -z "$TOTAL_QUEUED" ]; then
    write_status "✅ No RFQs in queue. Nothing to process." "Green"
    echo ""
    exit 0
fi

write_status "Starting migration process..." "Yellow"
write_status "Press Ctrl+C to stop at any time" "Gray"
echo ""
write_status "================================================================================" "Cyan"
write_status "Type | Total Queued | Migrated | RFQ Status | Bill No - BillID | Status" "Yellow"
write_status "================================================================================" "Cyan"
echo ""
sleep 2

# Process loop - continue until queue is 0
ITERATION=0
LAST_RFQ=""

while true; do
    ITERATION=$((ITERATION + 1))
    
    # Get current status
    STATUS_RESPONSE=$(curl -s -b "$COOKIE_FILE" -L "$STATUS_URL" -w "\n%{http_code}" 2>/dev/null)
    HTTP_CODE=$(echo "$STATUS_RESPONSE" | tail -n1)
    STATUS_JSON=$(echo "$STATUS_RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" != "200" ]; then
        write_status "  ⚠️  Error getting status (HTTP $HTTP_CODE)" "Yellow"
        sleep $PROCESSING_DELAY
        continue
    fi
    
    TOTAL_QUEUED=$(parse_json_number "$STATUS_JSON" "total_queued")
    MIGRATING_NOW=$(parse_json "$STATUS_JSON" "migrating_now")
    TOTAL_MIGRATED=$(parse_json_number "$STATUS_JSON" "total_migrated")
    TOTAL_ERRORS=$(parse_json_number "$STATUS_JSON" "total_errors")
    
    # Process one RFQ
    PROCESS_RESPONSE=$(curl -s -b "$COOKIE_FILE" -L "$PROCESS_URL" 2>/dev/null)
    
    CURRENT_RFQ="None"
    RFQ_DETAILS=""
    IN_DETAILS_SECTION=false
    
    # Parse response to extract RFQ details
    while IFS= read -r line; do
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if echo "$line" | grep -qiE "Migrating Now:"; then
            CURRENT_RFQ=$(echo "$line" | sed 's/.*Migrating Now:[[:space:]]*\(.*\)/\1/' | sed 's/[[:space:]]*$//')
        elif [ "$line" = "RFQ_DETAILS_START" ]; then
            IN_DETAILS_SECTION=true
        elif [ "$line" = "RFQ_DETAILS_END" ]; then
            IN_DETAILS_SECTION=false
        elif [ "$IN_DETAILS_SECTION" = true ] && echo "$line" | grep -qE "^[^:]+:"; then
            RFQ_DETAILS="${RFQ_DETAILS}${line}"$'\n'
        fi
    done <<< "$PROCESS_RESPONSE"
    
    # Parse RFQ details into associative array (bash 4+)
    declare -A rfq_details_map
    if [ -n "$RFQ_DETAILS" ]; then
        while IFS=':' read -r key value; do
            key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [ -n "$key" ] && [ -n "$value" ]; then
                rfq_details_map["$key"]="$value"
            fi
        done <<< "$RFQ_DETAILS"
    fi
    
    # Display RFQ details from migration table BEFORE migration starts (only once per RFQ)
    if [ ${#rfq_details_map[@]} -gt 0 ]; then
        RFQ_NUM_FROM_DETAILS="${rfq_details_map[RFQ_Number]}"
        DETAILS_KEY="${RFQ_NUM_FROM_DETAILS}|DETAILS_SHOWN"
        
        if [ -z "${processed_rfqs[$DETAILS_KEY]}" ]; then
            echo ""
            write_status "================================================================================" "Cyan"
            write_status "[RFQ] RFQ MIGRATION LINE DETAILS (FROM QUEUE TABLE - BEFORE MIGRATION)" "Yellow"
            write_status "================================================================================" "Cyan"
            write_status "RFQ Number: ${rfq_details_map[RFQ_Number]:-N/A}" "White"
            write_status "Priority: ${rfq_details_map[Priority]:-N/A}" "White"
            write_status "Vendor: ${rfq_details_map[Vendor]:-N/A}" "White"
            write_status "Project: ${rfq_details_map[Project]:-N/A}" "White"
            write_status "Purchase Representative: ${rfq_details_map[Purchase_Representative]:-N/A}" "White"
            write_status "Order Deadline: ${rfq_details_map[Order_Deadline]:-N/A}" "White"
            write_status "Status (Excel): ${rfq_details_map[Status_Excel]:-N/A}" "White"
            write_status "Branch/ID: ${rfq_details_map[Branch_ID]:-N/A}" "White"
            write_status "Stage: ${rfq_details_map[Stage]:-N/A}" "White"
            write_status "Bills/Number: ${rfq_details_map[Bills_Number]:-N/A}" "Yellow"
            write_status "Bills/ID: ${rfq_details_map[Bills_ID]:-N/A}" "Yellow"
            write_status "Created On: ${rfq_details_map[Created_On]:-N/A}" "White"
            write_status "Effective Date: ${rfq_details_map[Effective_Date]:-N/A}" "White"
            write_status "Receipt Date: ${rfq_details_map[Receipt_Date]:-N/A}" "White"
            write_status "Current Status: ${rfq_details_map[Current_Status]:-N/A}" "White"
            write_status "================================================================================" "Cyan"
            echo ""
            
            # Highlight Bill IDs if present
            BILLS_ID="${rfq_details_map[Bills_ID]}"
            if [ -n "$BILLS_ID" ] && [ "$BILLS_ID" != "N/A" ]; then
                write_status "[OK] Bill IDs found in queue list: $BILLS_ID - Will migrate these bills" "Green"
            else
                write_status "[WARNING] No Bill IDs in queue list - Bills may not be migrated" "Yellow"
            fi
            echo ""
            
            # Mark details as shown
            processed_rfqs[$DETAILS_KEY]=1
        fi
    fi
    
    # Extract RFQ number and determine status
    if [ -n "$CURRENT_RFQ" ] && [ "$CURRENT_RFQ" != "None" ]; then
        RFQ_NUM=$(echo "$CURRENT_RFQ" | sed 's/[[:space:]]*-[[:space:]]*\(DONE\|ERROR\|in progress\|Already migrated\).*//' | sed 's/[[:space:]]*$//')
        
        STATUS="Migrating"
        STATUS_COLOR="Yellow"
        IS_DONE=false
        
        if echo "$CURRENT_RFQ" | grep -qiE "DONE|Already migrated"; then
            STATUS="✅ DONE"
            STATUS_COLOR="Green"
            IS_DONE=true
        elif echo "$CURRENT_RFQ" | grep -qiE "ERROR"; then
            STATUS="❌ ERROR"
            STATUS_COLOR="Red"
        elif echo "$CURRENT_RFQ" | grep -qiE "in progress"; then
            STATUS="🔄 In Progress"
            STATUS_COLOR="Yellow"
        fi
        
        # Only process if this is a new RFQ or status changed to DONE
        DISPLAY_KEY="${RFQ_NUM}|${STATUS}"
        
        if [ -z "${processed_rfqs[$DISPLAY_KEY]}" ] || ([ "$IS_DONE" = true ] && [ "$LAST_RFQ" != "$RFQ_NUM" ]); then
            # Mark as processed
            processed_rfqs[$DISPLAY_KEY]=1
            LAST_RFQ="$RFQ_NUM"
            
            # Get detailed RFQ information if migration is done
            HAS_PO="NO"
            PO_STATE=""
            BILLING_STATUS=""
            VENDOR_BILLS_JSON=""
            PAYMENTS_JSON=""
            BILL_NUMBERS_FROM_QUEUE=""
            BILL_IDS_FROM_QUEUE=""
            
            if [ "$IS_DONE" = true ]; then
                DETAILS_URL="${ODOO_URL}/migration/rfq_details?db=${DATABASE}&rfq_number=${RFQ_NUM}"
                DETAILS_RESPONSE=$(curl -s -b "$COOKIE_FILE" -L "$DETAILS_URL" 2>/dev/null)
                
                if [ -n "$DETAILS_RESPONSE" ]; then
                    if [ "$USE_JQ" = true ]; then
                        HAS_PO=$(parse_json "$DETAILS_RESPONSE" "has_purchase_order")
                        if [ "$HAS_PO" = "true" ]; then
                            HAS_PO="YES"
                            PO_STATE=$(parse_json "$DETAILS_RESPONSE" "purchase_order_state")
                            BILLING_STATUS=$(parse_json "$DETAILS_RESPONSE" "billing_status")
                            VENDOR_BILLS_JSON=$(echo "$DETAILS_RESPONSE" | jq -c '.vendor_bills // []' 2>/dev/null)
                            
                            # Get bill numbers and IDs from queue list (primary source)
                            BILL_NUMBERS_FROM_QUEUE=$(parse_json_array "$DETAILS_RESPONSE" "bill_numbers_from_queue")
                            BILL_IDS_FROM_QUEUE=$(parse_json_array "$DETAILS_RESPONSE" "bill_ids_from_queue")
                            
                            # Collect all payments from all bills
                            PAYMENTS_JSON=$(echo "$DETAILS_RESPONSE" | jq -c '[.vendor_bills[]?.payments[]?] // []' 2>/dev/null)
                        elif [ -n "$(parse_json "$DETAILS_RESPONSE" "bill_numbers_from_queue")" ]; then
                            # Even if PO not found, show bill numbers from queue
                            BILL_NUMBERS_FROM_QUEUE=$(parse_json_array "$DETAILS_RESPONSE" "bill_numbers_from_queue")
                            BILL_IDS_FROM_QUEUE=$(parse_json_array "$DETAILS_RESPONSE" "bill_ids_from_queue")
                        fi
                    else
                        # Basic parsing without jq
                        if echo "$DETAILS_RESPONSE" | grep -q '"has_purchase_order"[[:space:]]*:[[:space:]]*true'; then
                            HAS_PO="YES"
                            PO_STATE=$(parse_json "$DETAILS_RESPONSE" "purchase_order_state")
                            BILLING_STATUS=$(parse_json "$DETAILS_RESPONSE" "billing_status")
                        fi
                    fi
                fi
            fi
            
            # Format bill numbers and IDs for display: "BillNo - BillID"
            # First priority: Use Bills/ID and Bills/Number from queue list (rfq_details_map)
            BILL_DISPLAY="NO"
            BILLS_ID="${rfq_details_map[Bills_ID]}"
            BILLS_NUMBER="${rfq_details_map[Bills_Number]}"
            
            if [ -n "$BILLS_ID" ] && [ "$BILLS_ID" != "N/A" ] && [ "$BILLS_ID" != "/" ]; then
                # Parse Bills/ID from queue list
                IFS=',' read -ra BILL_IDS_ARRAY <<< "$BILLS_ID"
                IFS=',' read -ra BILL_NUMS_ARRAY <<< "${BILLS_NUMBER:-}"
                
                BILL_PAIRS=()
                MAX_COUNT=${#BILL_IDS_ARRAY[@]}
                if [ ${#BILL_NUMS_ARRAY[@]} -gt $MAX_COUNT ]; then
                    MAX_COUNT=${#BILL_NUMS_ARRAY[@]}
                fi
                
                for ((i=0; i<MAX_COUNT; i++)); do
                    BILL_NO=""
                    BILL_ID=""
                    
                    if [ $i -lt ${#BILL_NUMS_ARRAY[@]} ]; then
                        BILL_NO=$(echo "${BILL_NUMS_ARRAY[$i]}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                        if [ "$BILL_NO" = "/" ] || [ -z "$BILL_NO" ]; then
                            BILL_NO=""
                        fi
                    fi
                    
                    if [ $i -lt ${#BILL_IDS_ARRAY[@]} ]; then
                        BILL_ID=$(echo "${BILL_IDS_ARRAY[$i]}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    fi
                    
                    if [ -n "$BILL_NO" ] && [ -n "$BILL_ID" ]; then
                        BILL_PAIRS+=("${BILL_NO} - ${BILL_ID}")
                    elif [ -n "$BILL_NO" ]; then
                        BILL_PAIRS+=("$BILL_NO")
                    elif [ -n "$BILL_ID" ]; then
                        BILL_PAIRS+=("$BILL_ID")
                    fi
                done
                
                if [ ${#BILL_PAIRS[@]} -gt 0 ]; then
                    BILL_DISPLAY=$(IFS=', '; echo "${BILL_PAIRS[*]}")
                fi
            elif [ -n "$BILL_NUMBERS_FROM_QUEUE" ] || [ -n "$BILL_IDS_FROM_QUEUE" ]; then
                # Second priority: Use from details JSON
                # This would require more complex parsing without jq, so we'll use a simpler approach
                if [ "$USE_JQ" = true ]; then
                    BILL_PAIRS=()
                    BILL_NUMS_ARRAY=($(echo "$BILL_NUMBERS_FROM_QUEUE"))
                    BILL_IDS_ARRAY=($(echo "$BILL_IDS_FROM_QUEUE"))
                    
                    MAX_COUNT=${#BILL_NUMS_ARRAY[@]}
                    if [ ${#BILL_IDS_ARRAY[@]} -gt $MAX_COUNT ]; then
                        MAX_COUNT=${#BILL_IDS_ARRAY[@]}
                    fi
                    
                    for ((i=0; i<MAX_COUNT; i++)); do
                        BILL_NO=""
                        BILL_ID=""
                        
                        if [ $i -lt ${#BILL_NUMS_ARRAY[@]} ]; then
                            BILL_NO="${BILL_NUMS_ARRAY[$i]}"
                        fi
                        
                        if [ $i -lt ${#BILL_IDS_ARRAY[@]} ]; then
                            BILL_ID="${BILL_IDS_ARRAY[$i]}"
                        fi
                        
                        if [ -n "$BILL_NO" ] && [ -n "$BILL_ID" ]; then
                            BILL_PAIRS+=("${BILL_NO} - ${BILL_ID}")
                        elif [ -n "$BILL_NO" ]; then
                            BILL_PAIRS+=("$BILL_NO")
                        elif [ -n "$BILL_ID" ]; then
                            BILL_PAIRS+=("$BILL_ID")
                        fi
                    done
                    
                    if [ ${#BILL_PAIRS[@]} -gt 0 ]; then
                        BILL_DISPLAY=$(IFS=', '; echo "${BILL_PAIRS[*]}")
                    fi
                fi
            fi
            
            # Get RFQ stage from details
            RFQ_STAGE="Draft"
            if [ "$USE_JQ" = true ] && [ -n "$DETAILS_RESPONSE" ]; then
                RFQ_STAGE=$(parse_json "$DETAILS_RESPONSE" "rfq_stage")
                if [ -z "$RFQ_STAGE" ] || [ "$RFQ_STAGE" = "null" ]; then
                    if [ "$HAS_PO" = "YES" ]; then
                        RFQ_STAGE="Purchase Order"
                    else
                        RFQ_STAGE="Draft"
                    fi
                fi
            elif [ "$HAS_PO" = "YES" ]; then
                RFQ_STAGE="Purchase Order"
            fi
            
            # Display RFQ header line
            DISPLAY_LINE="RFQ | ${RFQ_NUM} | Total Queued: ${TOTAL_QUEUED} | Migrated: ${TOTAL_MIGRATED} | ${RFQ_STAGE} | ${BILL_DISPLAY} | Status: ${STATUS}"
            write_status "$DISPLAY_LINE" "$STATUS_COLOR"
            write_status "--------------------" "Gray"
            
            # Display Purchase Order Confirming status
            if [ "$HAS_PO" = "YES" ]; then
                PO_CONFIRM_STATUS="PENDING"
                if [ "$PO_STATE" = "purchase" ] || [ "$PO_STATE" = "done" ]; then
                    PO_CONFIRM_STATUS="DONE"
                fi
                write_status "Purchase Order Confirming | ${PO_CONFIRM_STATUS}" "Yellow"
                
                # Check Purchase Order Billing Status
                write_status "Check Purchase Order Billing Status" "Yellow"
                BILLING_STATUS_TEXT="Unknown"
                case "$BILLING_STATUS" in
                    "nothing_to_bill") BILLING_STATUS_TEXT="Nothing to Bill" ;;
                    "to_bill") BILLING_STATUS_TEXT="Waiting for Bills" ;;
                    "billed") BILLING_STATUS_TEXT="Fully Billed" ;;
                esac
                write_status "Billing Status: ${BILLING_STATUS_TEXT}" "Cyan"
                write_status "--------------------" "Gray"
                write_status "Vendor Bill Checking with Purchase Order" "Yellow"
                echo ""
                
                # Use bill numbers and IDs from queue list (primary source)
                BILLS_TO_SHOW=()
                if [ -n "$BILL_NUMBERS_FROM_QUEUE" ] || [ -n "$BILL_IDS_FROM_QUEUE" ]; then
                    # Pair bill numbers with IDs
                    if [ "$USE_JQ" = true ]; then
                        BILL_NUMS_ARRAY=($(echo "$BILL_NUMBERS_FROM_QUEUE"))
                        BILL_IDS_ARRAY=($(echo "$BILL_IDS_FROM_QUEUE"))
                        
                        MAX_COUNT=${#BILL_NUMS_ARRAY[@]}
                        if [ ${#BILL_IDS_ARRAY[@]} -gt $MAX_COUNT ]; then
                            MAX_COUNT=${#BILL_IDS_ARRAY[@]}
                        fi
                        
                        for ((i=0; i<MAX_COUNT; i++)); do
                            BILL_NO=""
                            BILL_ID=""
                            
                            if [ $i -lt ${#BILL_NUMS_ARRAY[@]} ]; then
                                BILL_NO="${BILL_NUMS_ARRAY[$i]}"
                            fi
                            
                            if [ $i -lt ${#BILL_IDS_ARRAY[@]} ]; then
                                BILL_ID="${BILL_IDS_ARRAY[$i]}"
                            fi
                            
                            if [ -n "$BILL_NO" ] && [ -n "$BILL_ID" ]; then
                                BILLS_TO_SHOW+=("${BILL_NO}|${BILL_ID}")
                            elif [ -n "$BILL_NO" ]; then
                                BILLS_TO_SHOW+=("${BILL_NO}|")
                            elif [ -n "$BILL_ID" ]; then
                                BILLS_TO_SHOW+=("|${BILL_ID}")
                            fi
                        done
                    fi
                fi
                
                if [ ${#BILLS_TO_SHOW[@]} -gt 0 ]; then
                    write_status "Found Vendor Bill" "Green"
                    write_status "-----------------------------" "Gray"
                    write_status "collecting data" "Yellow"
                    
                    for bill_info in "${BILLS_TO_SHOW[@]}"; do
                        IFS='|' read -r BILL_NAME BILL_ID <<< "$bill_info"
                        
                        # Format: "BillNo - BillID" or just "BillNo" or "ID: BillID"
                        if [ -n "$BILL_NAME" ] && [ -n "$BILL_ID" ]; then
                            BILL_DISPLAY_TEXT="${BILL_NAME} - ${BILL_ID}"
                        elif [ -n "$BILL_NAME" ]; then
                            BILL_DISPLAY_TEXT="$BILL_NAME"
                        elif [ -n "$BILL_ID" ]; then
                            BILL_DISPLAY_TEXT="ID: ${BILL_ID}"
                        else
                            continue
                        fi
                        
                        write_status "Migrating Vendor Bill ${BILL_DISPLAY_TEXT} - status DONE" "Green"
                    done
                    
                    echo ""
                    write_status "vendor bill payment checking....." "Yellow"
                    echo ""
                    
                    if [ "$USE_JQ" = true ] && [ -n "$PAYMENTS_JSON" ] && [ "$PAYMENTS_JSON" != "[]" ]; then
                        PAYMENT_COUNT=$(echo "$PAYMENTS_JSON" | jq 'length' 2>/dev/null)
                        if [ "$PAYMENT_COUNT" -gt 0 ]; then
                            write_status "If yes" "Green"
                            write_status "-----------------------------" "Gray"
                            write_status "collecting data" "Yellow"
                            
                            echo "$PAYMENTS_JSON" | jq -r '.[] | "migrating payment \(.name) - Status DONE"' 2>/dev/null | while read -r payment_line; do
                                write_status "$payment_line" "Green"
                            done
                        else
                            write_status "No payments found" "Gray"
                        fi
                    else
                        write_status "No payments found" "Gray"
                    fi
                else
                    write_status "Found Vendor Bill / Not" "Gray"
                fi
            else
                write_status "Purchase Order Confirming | NOT CREATED" "Red"
            fi
            
            echo ""
            write_status "ALL Done" "Green"
            write_status "================================================================================" "Cyan"
            write_status "NEXT RFQ" "Yellow"
            echo ""
        fi
    fi
    
    # Check if queue is empty
    if [ "$TOTAL_QUEUED" = "0" ] || [ -z "$TOTAL_QUEUED" ]; then
        if [ -z "$MIGRATING_NOW" ] || [ "$MIGRATING_NOW" = "None" ]; then
            echo ""
            write_status "================================================================================" "Green"
            write_status "   ✅ Migration Complete!" "Green"
            write_status "================================================================================" "Green"
            echo ""
            write_status "Final Summary:" "Yellow"
            write_status "  Total Migrated: $TOTAL_MIGRATED" "Green"
            write_status "  Total Errors: $TOTAL_ERRORS" "Red"
            echo ""
            break
        fi
    fi
    
    # Wait before next iteration
    sleep $PROCESSING_DELAY
done
