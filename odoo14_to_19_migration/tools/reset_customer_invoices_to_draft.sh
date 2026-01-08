#!/bin/bash
# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Run the script using python3
python3 "$DIR/reset_customer_invoices_to_draft.py" "$@"
