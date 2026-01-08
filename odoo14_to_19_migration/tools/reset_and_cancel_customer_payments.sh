#!/bin/bash
cd "$(dirname "$0")"
python3 reset_and_cancel_customer_payments.py "$@"
