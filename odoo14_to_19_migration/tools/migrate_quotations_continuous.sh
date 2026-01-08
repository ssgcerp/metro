#!/bin/bash
# Shell script for Continuous Quotation Migration
# Processes all queued quotations one by one
# Shows each quotation on a line: Quotation | Total Queued | Migrated | Current Migration | Status
# List persists and grows as quotations are processed

# Configuration - Change these if needed
ODOO_URL="http://localhost:8079"
DATABASE="metrodb"  # Change this to your database name
PROCESSING_DELAY=2  # Seconds to wait between processing each quotation

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Track processed quotations to avoid duplicates
declare -A processed_quotations

# Function to print colored status
print_status() {
    local message="$1"
    local color="${2:-NC}"
    case "$color" in
        "Red") echo -e "${RED}${message}${NC}" ;;
        "Green") echo -e "${GREEN}${message}${NC}" ;;
        "Yellow") echo -e "${YELLOW}${message}${NC}" ;;
        "Cyan") echo -e "${CYAN}${message}${NC}" ;;
        "Gray") echo -e "${GRAY}${message}${NC}" ;;
        *) echo "$message" ;;
    esac
}

# Check if curl is available
if ! command -v curl &> /dev/null; then
    print_status "Error: curl is required but not installed." "Red"
    print_status "Please install curl: sudo apt-get install curl (Ubuntu/Debian) or sudo yum install curl (CentOS/RHEL)" "Yellow"
    exit 1
fi

# Check if jq is available (for JSON parsing)
if ! command -v jq &> /dev/null; then
    print_status "Warning: jq is not installed. JSON parsing will use basic methods." "Yellow"
    print_status "For better results, install jq: sudo apt-get install jq (Ubuntu/Debian) or sudo yum install jq (CentOS/RHEL)" "Yellow"
    USE_JQ=false
else
    USE_JQ=true
fi

echo ""
print_status "=== Quotation Migration Processor ===" "Cyan"
echo ""
print_status "Configuration:" "Yellow"
print_status "  Database: $DATABASE" "Gray"
print_status "  URL: $ODOO_URL" "Gray"
print_status "  Processing Delay: $PROCESSING_DELAY seconds" "Gray"
echo ""

# Step 1: Establish database session
print_status "Establishing database session..." "Yellow"
SESSION_COOKIE=$(mktemp)
if curl -s -c "$SESSION_COOKIE" "$ODOO_URL/web?db=$DATABASE" > /dev/null 2>&1; then
    print_status "  ✅ Session established" "Green"
else
    print_status "  ❌ Failed to establish session" "Red"
    print_status "     Please ensure Odoo is running and database '$DATABASE' exists" "Gray"
    rm -f "$SESSION_COOKIE"
    exit 1
fi
echo ""

# Get initial status
STATUS_URL="$ODOO_URL/migration/status?db=$DATABASE"
PROCESS_URL="$ODOO_URL/migration/process_one?db=$DATABASE"

if [ "$USE_JQ" = true ]; then
    STATUS_RESPONSE=$(curl -s -b "$SESSION_COOKIE" "$STATUS_URL")
    if [ $? -ne 0 ]; then
        print_status "  ❌ Error getting status" "Red"
        rm -f "$SESSION_COOKIE"
        exit 1
    fi
    
    TOTAL_QUEUED=$(echo "$STATUS_RESPONSE" | jq -r '.total_queued // 0')
    TOTAL_MIGRATED=$(echo "$STATUS_RESPONSE" | jq -r '.total_migrated // 0')
    TOTAL_ERRORS=$(echo "$STATUS_RESPONSE" | jq -r '.total_errors // 0')
else
    # Basic parsing without jq
    STATUS_RESPONSE=$(curl -s -b "$SESSION_COOKIE" "$STATUS_URL")
    if [ $? -ne 0 ]; then
        print_status "  ❌ Error getting status" "Red"
        rm -f "$SESSION_COOKIE"
        exit 1
    fi
    
    # Extract values using grep and sed (basic method)
    TOTAL_QUEUED=$(echo "$STATUS_RESPONSE" | grep -o '"total_queued":[0-9]*' | grep -o '[0-9]*' || echo "0")
    TOTAL_MIGRATED=$(echo "$STATUS_RESPONSE" | grep -o '"total_migrated":[0-9]*' | grep -o '[0-9]*' || echo "0")
    TOTAL_ERRORS=$(echo "$STATUS_RESPONSE" | grep -o '"total_errors":[0-9]*' | grep -o '[0-9]*' || echo "0")
fi

print_status "  ✅ Initial status retrieved" "Green"
echo ""

if [ "$TOTAL_QUEUED" -eq 0 ]; then
    print_status "✅ No quotations in queue. Nothing to process." "Green"
    echo ""
    rm -f "$SESSION_COOKIE"
    exit 0
fi

print_status "Starting migration process..." "Yellow"
print_status "Press Ctrl+C to stop at any time" "Gray"
echo ""
print_status "========================================" "Cyan"
print_status "Quotation | Total Queued | Migrated | Current Migration | Status" "Yellow"
print_status "========================================" "Cyan"
echo ""
sleep 2

# Process loop - continue until queue is 0
ITERATION=0

while true; do
    ITERATION=$((ITERATION + 1))
    
    # Get current status
    if [ "$USE_JQ" = true ]; then
        STATUS_RESPONSE=$(curl -s -b "$SESSION_COOKIE" "$STATUS_URL")
        if [ $? -eq 0 ]; then
            TOTAL_QUEUED=$(echo "$STATUS_RESPONSE" | jq -r '.total_queued // 0')
            MIGRATING_NOW=$(echo "$STATUS_RESPONSE" | jq -r '.migrating_now // "None"')
            TOTAL_MIGRATED=$(echo "$STATUS_RESPONSE" | jq -r '.total_migrated // 0')
            TOTAL_ERRORS=$(echo "$STATUS_RESPONSE" | jq -r '.total_errors // 0')
        else
            print_status "  ⚠️  Error getting status" "Yellow"
            sleep $PROCESSING_DELAY
            continue
        fi
    else
        STATUS_RESPONSE=$(curl -s -b "$SESSION_COOKIE" "$STATUS_URL")
        if [ $? -eq 0 ]; then
            TOTAL_QUEUED=$(echo "$STATUS_RESPONSE" | grep -o '"total_queued":[0-9]*' | grep -o '[0-9]*' || echo "0")
            MIGRATING_NOW=$(echo "$STATUS_RESPONSE" | grep -o '"migrating_now":"[^"]*"' | sed 's/"migrating_now":"\([^"]*\)"/\1/' || echo "None")
            TOTAL_MIGRATED=$(echo "$STATUS_RESPONSE" | grep -o '"total_migrated":[0-9]*' | grep -o '[0-9]*' || echo "0")
            TOTAL_ERRORS=$(echo "$STATUS_RESPONSE" | grep -o '"total_errors":[0-9]*' | grep -o '[0-9]*' || echo "0")
        else
            print_status "  ⚠️  Error getting status" "Yellow"
            sleep $PROCESSING_DELAY
            continue
        fi
    fi
    
    # Process one quotation
    PROCESS_RESPONSE=$(curl -s -b "$SESSION_COOKIE" "$PROCESS_URL")
    if [ $? -eq 0 ]; then
        # Extract current quotation from response
        CURRENT_QUOTATION=$(echo "$PROCESS_RESPONSE" | grep "Migrating Now:" | sed 's/.*Migrating Now: *\(.*\)/\1/' | tr -d '\r' | head -n1)
        
        if [ -z "$CURRENT_QUOTATION" ] || [ "$CURRENT_QUOTATION" = "None" ]; then
            CURRENT_QUOTATION="None"
        else
            # Extract quotation number and determine status
            QUOTATION_NUM=$(echo "$CURRENT_QUOTATION" | sed 's/ - .*//' | xargs)
            
            STATUS="Migrating"
            STATUS_COLOR="Yellow"
            if echo "$CURRENT_QUOTATION" | grep -q "DONE\|Already migrated"; then
                STATUS="✅ DONE"
                STATUS_COLOR="Green"
            elif echo "$CURRENT_QUOTATION" | grep -q "ERROR"; then
                STATUS="❌ ERROR"
                STATUS_COLOR="Red"
            elif echo "$CURRENT_QUOTATION" | grep -q "in progress"; then
                STATUS="🔄 In Progress"
                STATUS_COLOR="Yellow"
            fi
            
            # Create unique key for this quotation+status combination
            DISPLAY_KEY="${QUOTATION_NUM}|${STATUS}"
            
            # Only display if this is a new quotation or status changed
            if [ -z "${processed_quotations[$DISPLAY_KEY]}" ]; then
                # Mark as processed
                processed_quotations[$DISPLAY_KEY]=1
                
                # Display the line with all info
                DISPLAY_LINE="$QUOTATION_NUM | Total Queued: $TOTAL_QUEUED | Migrated: $TOTAL_MIGRATED | Current: $CURRENT_QUOTATION | Status: $STATUS"
                print_status "$DISPLAY_LINE" "$STATUS_COLOR"
            fi
        fi
    fi
    
    # Check if queue is empty
    if [ "$TOTAL_QUEUED" -eq 0 ] && ([ -z "$MIGRATING_NOW" ] || [ "$MIGRATING_NOW" = "None" ]); then
        echo ""
        print_status "========================================" "Green"
        print_status "   ✅ Migration Complete!" "Green"
        print_status "========================================" "Green"
        echo ""
        print_status "Final Summary:" "Yellow"
        print_status "  Total Migrated: $TOTAL_MIGRATED" "Green"
        print_status "  Total Errors: $TOTAL_ERRORS" "Red"
        echo ""
        break
    fi
    
    # Wait before next iteration
    sleep $PROCESSING_DELAY
done

# Cleanup
rm -f "$SESSION_COOKIE"

echo ""
print_status "Migration script completed." "Green"
echo ""

