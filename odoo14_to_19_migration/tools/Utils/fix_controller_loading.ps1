# Script to help diagnose and fix controller loading issues

Write-Host ""
Write-Host "=== Controller Loading Fix Guide ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Since ALL routes return 404 (including test route), controllers aren't loading." -ForegroundColor Yellow
Write-Host ""
Write-Host "Try these steps IN ORDER:" -ForegroundColor White
Write-Host ""

Write-Host "STEP 1: Check Odoo Server Logs" -ForegroundColor Green
Write-Host "  Look for Python errors related to:" -ForegroundColor Gray
Write-Host "    - migration_cron_controller" -ForegroundColor Gray
Write-Host "    - MigrationCronController" -ForegroundColor Gray
Write-Host "    - ImportError or SyntaxError" -ForegroundColor Gray
Write-Host ""

Write-Host "STEP 2: Reinstall Module (Not Just Upgrade)" -ForegroundColor Green
Write-Host "  1. Open: http://localhost:8079/web" -ForegroundColor White
Write-Host "  2. Go to: Apps" -ForegroundColor White
Write-Host "  3. Remove 'Apps' filter (click 'Apps' again)" -ForegroundColor White
Write-Host "  4. Search: odoo14_to_19_migration" -ForegroundColor White
Write-Host "  5. Click the module" -ForegroundColor White
Write-Host "  6. Click 'Uninstall' button" -ForegroundColor White
Write-Host "  7. Wait for uninstall to complete" -ForegroundColor White
Write-Host "  8. Click 'Install' button" -ForegroundColor White
Write-Host "  9. Wait for install to complete" -ForegroundColor White
Write-Host ""

Write-Host "STEP 3: FULLY Restart Odoo Server" -ForegroundColor Green
Write-Host "  - Stop the Odoo service/process completely" -ForegroundColor White
Write-Host "  - Wait 5 seconds" -ForegroundColor White
Write-Host "  - Start it again" -ForegroundColor White
Write-Host "  - Wait for server to fully load (check logs)" -ForegroundColor White
Write-Host ""

Write-Host "STEP 4: Test Again" -ForegroundColor Green
Write-Host "  Run: .\check_controller_loading.ps1" -ForegroundColor White
Write-Host ""

Write-Host "=== Alternative: Check Module Installation ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "If reinstalling doesn't work, verify:" -ForegroundColor Yellow
Write-Host "  1. Module is in addons path" -ForegroundColor White
Write-Host "  2. Module folder name matches: odoo14_to_19_migration" -ForegroundColor White
Write-Host "  3. No Python syntax errors in controller files" -ForegroundColor White
Write-Host "  4. Odoo can access the module directory" -ForegroundColor White
Write-Host ""

Write-Host "=== Quick Test Command ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "After restart, test with:" -ForegroundColor Yellow
Write-Host '  curl "http://localhost:8079/migration/test?db=metrodb"' -ForegroundColor White
Write-Host ""
Write-Host "Expected: 'OK - Controller is loaded and working!'" -ForegroundColor Green
Write-Host "If 404: Controllers still not loading - check logs" -ForegroundColor Red
Write-Host ""

