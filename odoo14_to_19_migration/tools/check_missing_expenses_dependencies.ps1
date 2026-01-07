$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Use Python to run the script
py "$ScriptDir\check_missing_expenses_dependencies.py" @args
