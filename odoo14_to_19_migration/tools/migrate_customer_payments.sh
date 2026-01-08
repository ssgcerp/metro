#!/bin/bash

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/Scripts/activate
elif [ -d "../.venv" ]; then
    source ../.venv/Scripts/activate
fi

# Run the migration script
# Ensure you are running this from the root of the workspace (e.g., e:/odoo modules/19/metro)
python odoo14_to_19_migration/tools/migrate_customer_payments.py "$@"
