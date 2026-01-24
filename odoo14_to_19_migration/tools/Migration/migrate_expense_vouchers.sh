#!/bin/bash
# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Use python3 to run the script
python3 "$DIR/migrate_expense_vouchers.py" "$@"
