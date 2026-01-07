$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Ensure pandas/openpyxl are installed
# py -m pip install pandas openpyxl
py "$ScriptDir\import_invoices_from_excel.py" @args
