#!/bin/bash
cd "$(dirname "$0")"
python3 export_odoo18_vendor_bills.py "$@"
