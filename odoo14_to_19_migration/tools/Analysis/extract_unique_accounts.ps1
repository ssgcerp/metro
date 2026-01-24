$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$PSScriptRoot\..\..\..\.venv\Scripts\python.exe" "$ScriptPath\extract_unique_accounts.py" @args
