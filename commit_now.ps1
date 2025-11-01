# Immediate commit and push script
$ErrorActionPreference = "Continue"
Write-Host "=== Committing and Pushing All Changes ===" -ForegroundColor Cyan

# Change to repository directory
Set-Location "E:\odoo modules\19\metro"

# Show status
Write-Host "`nCurrent status:" -ForegroundColor Yellow
git status --short

# Add all changes
Write-Host "`nAdding all changes..." -ForegroundColor Yellow
git add -A

# Show what will be committed
Write-Host "`nFiles to be committed:" -ForegroundColor Yellow
git status --short

# Commit
Write-Host "`nCommitting..." -ForegroundColor Yellow
$commitMsg = "Auto-commit: Update estimation form layout, add module analysis and auto-commit script"
git commit -m $commitMsg

# Push
Write-Host "`nPushing to remote..." -ForegroundColor Yellow
git push origin main

# Verify
Write-Host "`nVerifying..." -ForegroundColor Yellow
git log --oneline -3

Write-Host "`n=== Done ===" -ForegroundColor Green

