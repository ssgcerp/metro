$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Use Python to run the script
py "$ScriptDir\merge_duplicate_vendors.py" @args
