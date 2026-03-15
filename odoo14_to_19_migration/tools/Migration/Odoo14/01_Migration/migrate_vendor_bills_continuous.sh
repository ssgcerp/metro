#!/bin/bash
# Bash script for Continuous Vendor Bill Migration
# Processes all queued vendor bills one by one
# Shows each bill on a line: Bill | Total Queued | Migrated | Current Migration | Status
# List persists and grows as bills are processed

# Configuration - Change these if needed
ODOO_URL="https://metro.equdaierp.com"
DATABASE="newdb"  # Change this to your database name
PROCESSING_DELAY=2  # Seconds to wait between processing each bill

# Colors for output
NC='\033[0m' # No Color
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[1;30m'

function write_status() {
    local message="$1"
    local color="$2"
    case "$color" in
        "Red") echo -e "${RED}${message}${NC}" ;;
        "Green") echo -e "${GREEN}${message}${NC}" ;;
        "Yellow") echo -e "${YELLOW}${message}${NC}" ;;
        "Cyan") echo -e "${CYAN}${message}${NC}" ;;
        "Gray") echo -e "${GRAY}${message}${NC}" ;;
        *) echo -e "${message}" ;;
    esac
}

# Track processed bills to avoid duplicates
declare -A PROCESSED_BILLS

write_status "" ""
write_status "=== Vendor Bill Migration Processor ===" "Cyan"
write_status "" ""
write_status "Configuration:" "Yellow"
write_status "  Database: $DATABASE" "Gray"
write_status "  URL: $ODOO_URL" "Gray"
write_status "  Processing Delay: $PROCESSING_DELAY seconds" "Gray"
write_status "" ""

# Step 1: Establish database session
write_status "Establishing database session..." "Yellow"
COOKIE_FILE=$(mktemp)
trap 'rm -f "$COOKIE_FILE"' EXIT

if ! curl -s -c "$COOKIE_FILE" "$ODOO_URL/web?db=$DATABASE" > /dev/null; then
    write_status "  ❌ Failed to establish session" "Red"
    write_status "     Please ensure Odoo is running and database '$DATABASE' exists" "Gray"
    exit 1
fi
write_status "  ✅ Session established" "Green"
write_status "" ""

STATUS_URL="$ODOO_URL/migration/status_vendor_bill?db=$DATABASE"
PROCESS_URL="$ODOO_URL/migration/process_one_vendor_bill?db=$DATABASE"

# Get initial status
INITIAL_STATUS=$(curl -s -b "$COOKIE_FILE" "$STATUS_URL")

# Check if route not found (html response instead of json)
if echo "$INITIAL_STATUS" | grep -iq "<html"; then
    write_status "  ❌ Route not found (404) or returned HTML" "Red"
    write_status "     Please upgrade the module: Apps > odoo14_to_19_migration > Upgrade" "Yellow"
    write_status "     Then FULLY restart Odoo server" "Yellow"
    exit 1
fi

# Parse JSON safely with Python
PARSED_JSON=$(echo "$INITIAL_STATUS" | python3 -c "import sys, json;
try:
    d = json.load(sys.stdin)
    print(f\"{d.get('total_queued', 0)}|{d.get('total_migrated', 0)}|{d.get('total_errors', 0)}\")
except:
    print('')
")

TOTAL_QUEUED=$(echo "$PARSED_JSON" | cut -d'|' -f1)
TOTAL_MIGRATED=$(echo "$PARSED_JSON" | cut -d'|' -f2)
TOTAL_ERRORS=$(echo "$PARSED_JSON" | cut -d'|' -f3)

if [ -z "$TOTAL_QUEUED" ]; then
    write_status "  ❌ Error getting initial status. Response: $INITIAL_STATUS" "Red"
    exit 1
fi

write_status "  ✅ Initial status retrieved" "Green"
write_status "" ""

if [ "$TOTAL_QUEUED" -eq 0 ]; then
    write_status "✅ No vendor bills in queue. Nothing to process." "Green"
    write_status "" ""
    exit 0
fi

write_status "Starting migration process..." "Yellow"
write_status "Press Ctrl+C to stop at any time" "Gray"
write_status "" ""
write_status "========================================" "Cyan"
write_status "Bill | Total Queued | Migrated | Odoo 14 Products | Odoo 19 Products | Current Migration | Status" "Yellow"
write_status "========================================" "Cyan"
write_status "" ""
sleep 2

while true; do
    # Get current status
    STATUS_RESP=$(curl -s -b "$COOKIE_FILE" "$STATUS_URL")
    if [ -z "$STATUS_RESP" ]; then
        write_status "  ⚠️  Error getting status: Empty response" "Yellow"
        sleep "$PROCESSING_DELAY"
        continue
    fi
    
    PARSED_STATUS=$(echo "$STATUS_RESP" | python3 -c "import sys, json;
try:
    d = json.load(sys.stdin)
    print(f\"{d.get('total_queued', 0)}|{d.get('migrating_now', 'None')}|{d.get('total_migrated', 0)}|{d.get('total_errors', 0)}\")
except:
    print('')
")
    
    TOTAL_QUEUED=$(echo "$PARSED_STATUS" | cut -d'|' -f1)
    MIGRATING_NOW=$(echo "$PARSED_STATUS" | cut -d'|' -f2)
    TOTAL_MIGRATED=$(echo "$PARSED_STATUS" | cut -d'|' -f3)
    TOTAL_ERRORS=$(echo "$PARSED_STATUS" | cut -d'|' -f4)
    
    # Process one vendor bill
    PROCESS_RESP=$(curl -s -b "$COOKIE_FILE" "$PROCESS_URL")
    
    CURRENT_BILL="None"
    if echo "$PROCESS_RESP" | grep -q "Migrating Now:"; then
        CURRENT_BILL=$(echo "$PROCESS_RESP" | grep "Migrating Now:" | sed -e 's/.*Migrating Now:\s*//' | head -n1 | tr -d '\r')
    fi
    
    if [ -n "$CURRENT_BILL" ] && [ "$CURRENT_BILL" != "None" ]; then
        BILL_NUM=$(echo "$CURRENT_BILL" | sed -E 's/\s*-\s*(DONE|ERROR|in progress|Already migrated).*//' | xargs)
        
        STATUS="Migrating"
        STATUS_COLOR="Yellow"
        
        if echo "$CURRENT_BILL" | grep -Eq "DONE|Already migrated"; then
            STATUS="✅ DONE"
            STATUS_COLOR="Green"
        elif echo "$CURRENT_BILL" | grep -q "ERROR"; then
            STATUS="❌ ERROR"
            STATUS_COLOR="Red"
        elif echo "$CURRENT_BILL" | grep -q "in progress"; then
            STATUS="🔄 In Progress"
            STATUS_COLOR="Yellow"
        fi
        
        DISPLAY_KEY="${BILL_NUM}|${STATUS}"
        
        if [ -z "${PROCESSED_BILLS[$DISPLAY_KEY]}" ]; then
            PROCESSED_BILLS[$DISPLAY_KEY]=1
            DISPLAY_LINE="${BILL_NUM} | Total Queued: ${TOTAL_QUEUED} | Migrated: ${TOTAL_MIGRATED} | Current: ${CURRENT_BILL} | Status: ${STATUS}"
            write_status "$DISPLAY_LINE" "$STATUS_COLOR"
        fi
    fi
    
    if [ "$TOTAL_QUEUED" -eq 0 ] && [[ "$MIGRATING_NOW" == "None" || "$MIGRATING_NOW" == "null" || -z "$MIGRATING_NOW" ]]; then
        write_status "" ""
        write_status "========================================" "Green"
        write_status "   ✅ Migration Complete!" "Green"
        write_status "========================================" "Green"
        write_status "" ""
        write_status "Final Summary:" "Yellow"
        write_status "  Total Migrated: $TOTAL_MIGRATED" "Green"
        write_status "  Total Errors: $TOTAL_ERRORS" "Red"
        write_status "" ""
        break
    fi
    
    sleep "$PROCESSING_DELAY"
done
