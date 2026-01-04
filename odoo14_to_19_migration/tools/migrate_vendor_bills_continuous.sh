#!/bin/bash
# Bash script for Continuous Vendor Bill Migration (Linux/Unix)
# Processes all queued vendor bills one by one
# Shows each bill on a line: Bill | Total Queued | Migrated | Odoo 14 Products | Odoo 19 Products | Current Migration | Status

# Configuration - Change these if needed
ODOO_URL="http://localhost:8079"
DATABASE="metrodb"  # Change this to your database name
PROCESSING_DELAY=2  # Seconds to wait between processing each bill

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Track processed bills to avoid duplicates
declare -A processed_bills

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

# Create temporary cookie file for session management
COOKIE_FILE=$(mktemp)
trap "rm -f $COOKIE_FILE" EXIT

echo ""
write_status "=== Vendor Bill Migration Processor ===" "Cyan"
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
STATUS_URL="$ODOO_URL/migration/status_vendor_bill?db=$DATABASE"
PROCESS_URL="$ODOO_URL/migration/process_one_vendor_bill?db=$DATABASE"

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
    write_status "✅ No vendor bills in queue. Nothing to process." "Green"
    echo ""
    exit 0
fi

write_status "Starting migration process..." "Yellow"
write_status "Press Ctrl+C to stop at any time" "Gray"
echo ""
write_status "========================================" "Cyan"
write_status "Bill | Total Queued | Migrated | Odoo 14 Products | Odoo 19 Products | Current Migration | Status" "Yellow"
write_status "========================================" "Cyan"
echo ""
sleep 2

# Process loop - continue until queue is 0
ITERATION=0

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
    
    # Process one vendor bill
    PROCESS_RESPONSE=$(curl -s -b "$COOKIE_FILE" -L "$PROCESS_URL" 2>/dev/null)
    
    CURRENT_BILL="None"
    
    # Initialize bill details
    BILL_NUMBER=""
    VENDOR=""
    AMOUNT=0.0
    PAYMENTS=0
    TOTAL_ITEMS_ODOO14=0
    TOTAL_ITEMS_MIGRATED=0
    PRODUCTS_ODOO14=0
    PRODUCTS_ODOO19=0
    IN_DETAILS_SECTION=false
    
    # Parse response to extract bill details
    while IFS= read -r line; do
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if echo "$line" | grep -qiE "Migrating Now:"; then
            CURRENT_BILL=$(echo "$line" | sed 's/.*Migrating Now:[[:space:]]*\(.*\)/\1/' | sed 's/[[:space:]]*$//')
        fi
        
        # Parse bill details section
        if echo "$line" | grep -qiE "Migrating Vendor Bill details:"; then
            IN_DETAILS_SECTION=true
        elif [ "$IN_DETAILS_SECTION" = true ]; then
            if echo "$line" | grep -qiE "Bill Number:"; then
                BILL_NUMBER=$(echo "$line" | sed 's/.*Bill Number:[[:space:]]*\(.*\)/\1/' | sed 's/[[:space:]]*$//')
            elif echo "$line" | grep -qiE "Vendor:"; then
                VENDOR=$(echo "$line" | sed 's/.*Vendor:[[:space:]]*\(.*\)/\1/' | sed 's/[[:space:]]*$//')
            elif echo "$line" | grep -qiE "Total Bill Amount:"; then
                AMOUNT_STR=$(echo "$line" | sed 's/.*Total Bill Amount:[[:space:]]*\([0-9,]*\.\?[0-9]*\)/\1/' | sed 's/,//g')
                AMOUNT=$(echo "$AMOUNT_STR" | awk '{print $1+0}')
            elif echo "$line" | grep -qiE "Payments Linked:"; then
                PAYMENTS=$(echo "$line" | sed 's/.*Payments Linked:[[:space:]]*\([0-9]*\)/\1/' | awk '{print $1+0}')
            elif echo "$line" | grep -qiE "Total Items \(Odoo 14\):"; then
                TOTAL_ITEMS_ODOO14=$(echo "$line" | sed 's/.*Total Items (Odoo 14):[[:space:]]*\([0-9]*\)/\1/' | awk '{print $1+0}')
            elif echo "$line" | grep -qiE "Total Items Migrated:"; then
                TOTAL_ITEMS_MIGRATED=$(echo "$line" | sed 's/.*Total Items Migrated:[[:space:]]*\([0-9]*\)/\1/' | awk '{print $1+0}')
            elif echo "$line" | grep -qiE "Products \(Odoo 14\):"; then
                PRODUCTS_ODOO14=$(echo "$line" | sed 's/.*Products (Odoo 14):[[:space:]]*\([0-9]*\)/\1/' | awk '{print $1+0}')
            elif echo "$line" | grep -qiE "Products Migrated:"; then
                PRODUCTS_ODOO19=$(echo "$line" | sed 's/.*Products Migrated:[[:space:]]*\([0-9]*\)/\1/' | awk '{print $1+0}')
            elif [ -z "$line" ] || echo "$line" | grep -qiE "Total Queued:"; then
                IN_DETAILS_SECTION=false
            fi
        fi
    done <<< "$PROCESS_RESPONSE"
    
    # Extract bill number and determine status
    if [ -n "$CURRENT_BILL" ] && [ "$CURRENT_BILL" != "None" ]; then
        BILL_NUM=$(echo "$CURRENT_BILL" | sed 's/[[:space:]]*-[[:space:]]*\(DONE\|ERROR\|in progress\|Already migrated\).*//' | sed 's/[[:space:]]*$//')
        
        # Use bill number from details if available
        if [ -n "$BILL_NUMBER" ] && [ "$BILL_NUMBER" != "N/A" ]; then
            BILL_NUM="$BILL_NUMBER"
        fi
        
        STATUS="Migrating"
        STATUS_COLOR="Yellow"
        
        if echo "$CURRENT_BILL" | grep -qiE "DONE|Already migrated"; then
            STATUS="✅ DONE"
            STATUS_COLOR="Green"
        elif echo "$CURRENT_BILL" | grep -qiE "ERROR"; then
            STATUS="❌ ERROR"
            STATUS_COLOR="Red"
        elif echo "$CURRENT_BILL" | grep -qiE "in progress"; then
            STATUS="🔄 In Progress"
            STATUS_COLOR="Yellow"
        fi
        
        # Create unique key for this bill+status combination
        DISPLAY_KEY="${BILL_NUM}|${STATUS}"
        
        # Only display if this is a new bill or status changed
        if [ -z "${processed_bills[$DISPLAY_KEY]}" ]; then
            # Mark as processed
            processed_bills[$DISPLAY_KEY]=1
            
            # Display bill details header if available
            if [ -n "$BILL_NUMBER" ] && [ "$BILL_NUMBER" != "N/A" ] && [ -n "$BILL_NUMBER" ]; then
                echo ""
                write_status "Migrating Vendor Bill details" "Cyan"
                write_status "Bill Number: $BILL_NUMBER" "Gray"
                if [ -n "$VENDOR" ] && [ "$VENDOR" != "N/A" ]; then
                    write_status "Vendor: $VENDOR" "Gray"
                fi
                if [ "$(echo "$AMOUNT > 0" | bc 2>/dev/null || echo 0)" = "1" ]; then
                    write_status "Total Bill Amount: $(printf "%.2f" "$AMOUNT" 2>/dev/null || echo "$AMOUNT")" "Gray"
                fi
                if [ "$TOTAL_ITEMS_ODOO14" -gt 0 ] 2>/dev/null; then
                    write_status "Total Items: $TOTAL_ITEMS_ODOO14" "Cyan"
                fi
                if [ "$TOTAL_ITEMS_MIGRATED" -gt 0 ] 2>/dev/null; then
                    write_status "Total Items Migrated: $TOTAL_ITEMS_MIGRATED" "Green"
                fi
                if [ "$PAYMENTS" -gt 0 ] 2>/dev/null; then
                    write_status "Payments Linked: $PAYMENTS" "Green"
                fi
                echo ""
            fi
            
            # Display the line with all info
            PRODUCTS14_STR="N/A"
            if [ "$PRODUCTS_ODOO14" -gt 0 ] 2>/dev/null; then
                PRODUCTS14_STR="$PRODUCTS_ODOO14"
            fi
            
            PRODUCTS19_STR="N/A"
            if [ "$PRODUCTS_ODOO19" -gt 0 ] 2>/dev/null; then
                PRODUCTS19_STR="$PRODUCTS_ODOO19"
            fi
            
            DISPLAY_LINE="${BILL_NUM} | Total Queued: ${TOTAL_QUEUED} | Migrated: ${TOTAL_MIGRATED} | Odoo 14 Products: ${PRODUCTS14_STR} | Odoo 19 Products: ${PRODUCTS19_STR} | Current: ${CURRENT_BILL} | Status: ${STATUS}"
            write_status "$DISPLAY_LINE" "$STATUS_COLOR"
        fi
    fi
    
    # Check if queue is empty
    if [ "$TOTAL_QUEUED" = "0" ] || [ -z "$TOTAL_QUEUED" ]; then
        if [ -z "$MIGRATING_NOW" ] || [ "$MIGRATING_NOW" = "None" ]; then
            echo ""
            write_status "========================================" "Green"
            write_status "   ✅ Migration Complete!" "Green"
            write_status "========================================" "Green"
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
