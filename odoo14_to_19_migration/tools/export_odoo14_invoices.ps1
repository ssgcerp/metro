$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Ensure pandas/openpyxl are installed
# py -m pip install pandas openpyxl
py "$ScriptDir\export_odoo14_invoices.py" @args
