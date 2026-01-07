$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Use Python to run the script
py "$ScriptDir\create_missing_coa.py" @args
