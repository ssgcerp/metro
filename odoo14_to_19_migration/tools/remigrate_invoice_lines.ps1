$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
py "$ScriptDir\remigrate_invoice_lines.py" @args
