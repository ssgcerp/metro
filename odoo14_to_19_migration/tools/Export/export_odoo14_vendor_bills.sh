#!/bin/bash
cd "$(dirname "$0")"
python3 export_odoo14_vendor_bills.py "$@"
