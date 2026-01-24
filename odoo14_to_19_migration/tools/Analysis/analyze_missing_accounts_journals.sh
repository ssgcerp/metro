#!/bin/bash
cd "$(dirname "$0")"
python3 analyze_missing_accounts_journals.py "$@"
