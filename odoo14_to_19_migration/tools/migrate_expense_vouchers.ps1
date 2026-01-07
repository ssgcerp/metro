$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Use Python to run the script
py "$ScriptDir\migrate_expense_vouchers.py" @args
