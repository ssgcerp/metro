$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptPath\export_odoo14_vendor_bills.py" @args
