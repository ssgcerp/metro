$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
py "$ScriptDir\fix_fallback_invoices.py" @args
