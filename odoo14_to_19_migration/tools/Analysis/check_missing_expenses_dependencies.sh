#!/bin/bash
SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
python3 "$SCRIPTPATH/check_missing_expenses_dependencies.py" "$@"
