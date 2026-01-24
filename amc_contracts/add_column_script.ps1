# PowerShell script to add branch_code column
# Run this script in PowerShell

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "Adding branch_code column to database" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Database connection details - UPDATE THESE IF NEEDED
$dbName = "metro1"
$dbUser = "odoo"
$dbHost = "localhost"
$dbPort = "5432"

Write-Host "Database: $dbName" -ForegroundColor Yellow
Write-Host "User: $dbUser" -ForegroundColor Yellow
Write-Host ""

# Check if psql is available
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue

if (-not $psqlPath) {
    Write-Host "ERROR: psql command not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run this SQL manually in pgAdmin:" -ForegroundColor Yellow
    Write-Host "  ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);" -ForegroundColor White
    Write-Host ""
    Write-Host "Or install PostgreSQL client tools and try again." -ForegroundColor Yellow
    pause
    exit
}

# Prompt for password
$dbPassword = Read-Host "Enter PostgreSQL password for user '$dbUser'" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

$env:PGPASSWORD = $plainPassword

# Run SQL
Write-Host "Running SQL..." -ForegroundColor Yellow

$sqlCommand = "ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);"

$result = & psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -c $sqlCommand 2>&1

# Clear password from environment
Remove-Variable env:PGPASSWORD -ErrorAction SilentlyContinue

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host "SUCCESS! Column added successfully." -ForegroundColor Green
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Now RESTART your Odoo server and refresh browser." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "=======================================" -ForegroundColor Red
    Write-Host "ERROR occurred!" -ForegroundColor Red
    Write-Host "=======================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Output: $result" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please run this SQL manually in pgAdmin:" -ForegroundColor Yellow
    Write-Host "  ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);" -ForegroundColor White
}

Write-Host ""
pause






