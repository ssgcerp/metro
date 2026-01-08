#!/bin/bash

# Bash wrapper for Reset Customer Invoices
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/reset_customer_invoices_to_draft.py"

echo -e "\033[0;36mRunning script: $PYTHON_SCRIPT\033[0m"

# Check for python3 or python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "\033[0;31mPython not found. Please install Python.\033[0m"
    exit 1
fi

# Run the python script
"$PYTHON_CMD" "$PYTHON_SCRIPT"

if [ $? -eq 0 ]; then
    echo -e "\033[0;32mProcess completed successfully.\033[0m"
else
    echo -e "\033[0;31mProcess failed.\033[0m"
fi

read -p "Press Enter to exit..."
