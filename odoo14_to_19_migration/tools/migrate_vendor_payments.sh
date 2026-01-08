#!/bin/bash
cd "$(dirname "$0")"
python3 migrate_vendor_payments.py "$@"
