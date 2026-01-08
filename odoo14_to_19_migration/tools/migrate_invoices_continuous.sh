#!/bin/bash
# Bash script for Continuous Customer Invoice Migration (Linux/Unix)
# Processes all queued invoices one by one
# Shows each invoice on a line: Invoice | Total Queued | Migrated | Current Migration | Status

# Configuration - Change these if needed
ODOO_URL="http://localhost:8079"
DATABASE="metrodb"  # Change this to your database name
PROCESSING_DELAY=2  # Seconds to wait between processing each invoice

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Track processed invoices to avoid duplicates
declare -A processed_invoices

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
write_status "=== Customer Invoice Migration Processor ===" "Cyan"
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
STATUS_URL="$ODOO_URL/migration/status_invoice?db=$DATABASE"
PROCESS_URL="$ODOO_URL/migration/process_one_invoice?db=$DATABASE"

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
    write_status "✅ No invoices in queue. Nothing to process." "Green"
    echo ""
    exit 0
fi

write_status "Starting migration process..." "Yellow"
write_status "Press Ctrl+C to stop at any time" "Gray"
echo ""
write_status "========================================" "Cyan"
write_status "Invoice | Total Queued | Migrated | Current Migration | Status" "Yellow"
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
    
    # Process one invoice
    PROCESS_RESPONSE=$(curl -s -b "$COOKIE_FILE" -L "$PROCESS_URL" 2>/dev/null)
    
    CURRENT_INVOICE="None"
    
    # Parse response to extract invoice details
    while IFS= read -r line; do
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if echo "$line" | grep -qiE "Migrating Now:"; then
            CURRENT_INVOICE=$(echo "$line" | sed 's/.*Migrating Now:[[:space:]]*\(.*\)/\1/' | sed 's/[[:space:]]*$//')
        fi
    done <<< "$PROCESS_RESPONSE"
    
    # Extract invoice number and determine status
    if [ -n "$CURRENT_INVOICE" ] && [ "$CURRENT_INVOICE" != "None" ]; then
        INVOICE_NUM=$(echo "$CURRENT_INVOICE" | sed 's/[[:space:]]*-[[:space:]]*\(DONE\|ERROR\|in progress\|Already migrated\).*//' | sed 's/[[:space:]]*$//')
        
        STATUS="Migrating"
        STATUS_COLOR="Yellow"
        
        if echo "$CURRENT_INVOICE" | grep -qiE "DONE|Already migrated"; then
            STATUS="✅ DONE"
            STATUS_COLOR="Green"
        elif echo "$CURRENT_INVOICE" | grep -qiE "ERROR"; then
            STATUS="❌ ERROR"
            STATUS_COLOR="Red"
        elif echo "$CURRENT_INVOICE" | grep -qiE "in progress"; then
            STATUS="🔄 In Progress"
            STATUS_COLOR="Yellow"
        fi
        
        # Create unique key for this invoice+status combination
        DISPLAY_KEY="${INVOICE_NUM}|${STATUS}"
        
        # Only display if this is a new invoice or status changed
        if [ -z "${processed_invoices[$DISPLAY_KEY]}" ]; then
            # Mark as processed
            processed_invoices[$DISPLAY_KEY]=1
            
            # Display the line with all info
            DISPLAY_LINE="${INVOICE_NUM} | Total Queued: ${TOTAL_QUEUED} | Migrated: ${TOTAL_MIGRATED} | Current: ${CURRENT_INVOICE} | Status: ${STATUS}"
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
