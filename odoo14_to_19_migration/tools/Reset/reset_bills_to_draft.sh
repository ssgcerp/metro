#!/bin/bash
# Wrapper to run the Python script to reset vendor bills
# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
SCRIPT_PATH="$SCRIPT_DIR/reset_bills_to_draft.py"

echo "Running script: $SCRIPT_PATH"

# Check if python3 or python is available
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
elif command -v py &>/dev/null; then
    PYTHON_CMD="py"
else
    echo "Error: Python not found. Please install Python."
    exit 1
fi

"$PYTHON_CMD" "$SCRIPT_PATH"

if [ $? -eq 0 ]; then
    echo -e "\033[0;32mReset process completed successfully.\033[0m"
else
    echo -e "\033[0;31mReset process failed.\033[0m"
fi

read -p "Press Enter to exit..."
