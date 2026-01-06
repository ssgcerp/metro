# Wrapper to run the Python script to reset vendor bills
$ScriptPath = Join-Path $PSScriptRoot "reset_bills_to_draft.py"
Write-Host "Running script: $ScriptPath" -ForegroundColor Cyan

# Run python script
py $ScriptPath

if ($LASTEXITCODE -eq 0) {
    Write-Host "Reset process completed successfully." -ForegroundColor Green
}
else {
    Write-Host "Reset process failed." -ForegroundColor Red
}

Read-Host "Press Enter to exit..."
