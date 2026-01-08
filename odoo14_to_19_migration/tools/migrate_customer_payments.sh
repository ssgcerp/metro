#!/bin/bash
# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Run the migration script using python3
python3 "$DIR/migrate_customer_payments.py" "$@"
