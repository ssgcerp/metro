$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptPath\migrate_vendor_payments.py" @args
