$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptPath\reset_and_cancel_customer_payments.py" @args
