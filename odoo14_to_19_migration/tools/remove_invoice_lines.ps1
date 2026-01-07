$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
py "$ScriptDir\remove_invoice_lines.py" @args
