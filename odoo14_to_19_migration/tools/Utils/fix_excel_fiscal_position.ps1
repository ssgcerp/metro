$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptPath\fix_excel_fiscal_position.py" @args
