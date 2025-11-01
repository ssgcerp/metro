# Auto Commit and Push Script for Git Repository
# This script automatically commits all changes and pushes to remote

param(
    [string]$CommitMessage = "Auto-commit: Changes made during development session"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Auto Commit and Push Script ===" -ForegroundColor Cyan
Write-Host ""

# Get current directory
$RepoPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoPath

Write-Host "Repository: $RepoPath" -ForegroundColor Yellow
Write-Host ""

# Check if git repository
if (-not (Test-Path ".git")) {
    Write-Host "Error: Not a git repository!" -ForegroundColor Red
    exit 1
}

# Check git status
Write-Host "Checking git status..." -ForegroundColor Yellow
$status = git status --porcelain

if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "No changes to commit." -ForegroundColor Green
    exit 0
}

# Show status
Write-Host "Changes detected:" -ForegroundColor Yellow
git status --short
Write-Host ""

# Add all changes
Write-Host "Adding all changes..." -ForegroundColor Yellow
git add -A

# Commit
Write-Host "Committing changes..." -ForegroundColor Yellow
try {
    git commit -m $CommitMessage
    Write-Host "✓ Committed successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Commit failed: $_" -ForegroundColor Red
    exit 1
}

# Push
Write-Host "Pushing to remote..." -ForegroundColor Yellow
try {
    git push origin main
    Write-Host "✓ Pushed successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Push failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan

