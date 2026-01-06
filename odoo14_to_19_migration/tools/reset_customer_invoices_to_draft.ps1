# PowerShell wrapper for Reset Customer Invoices
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "reset_customer_invoices_to_draft.py"

Write-Host "Running script: $PythonScript" -ForegroundColor Cyan

# Check for 'py' launcher first, then 'python'
if (Get-Command "py" -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}
elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
}
else {
    Write-Error "Python not found. Please install Python."
    exit 1
}

# Run the python script
& $PythonCmd $PythonScript

if ($LASTEXITCODE -eq 0) {
    Write-Host "Process completed successfully." -ForegroundColor Green
}
else {
    Write-Host "Process failed." -ForegroundColor Red
}

Read-Host "Press Enter to exit..."
