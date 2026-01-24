$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptPath\analyze_missing_accounts_journals.py" @args
