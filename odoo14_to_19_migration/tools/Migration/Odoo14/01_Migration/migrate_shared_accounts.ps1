$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$PSScriptRoot\..\..\..\.venv\Scripts\python.exe" "$ScriptPath\migrate_shared_accounts.py" @args
