# Script to help check Odoo logs for controller loading errors

Write-Host ""
Write-Host "=== Odoo Controller Loading Diagnostic ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Since ALL controllers return 404, they're not loading." -ForegroundColor Yellow
Write-Host ""
Write-Host "This usually means:" -ForegroundColor White
Write-Host "  1. Python import error preventing controller loading" -ForegroundColor Gray
Write-Host "  2. Module not properly installed" -ForegroundColor Gray
Write-Host "  3. Server needs full restart" -ForegroundColor Gray
Write-Host "  4. Syntax error in controller files" -ForegroundColor Gray
Write-Host ""

Write-Host "=== Check Odoo Server Logs ===" -ForegroundColor Green
Write-Host ""
Write-Host "Look for errors containing:" -ForegroundColor Yellow
Write-Host "  - 'migration_cron_controller'" -ForegroundColor White
Write-Host "  - 'MigrationCronController'" -ForegroundColor White
Write-Host "  - 'ImportError'" -ForegroundColor White
Write-Host "  - 'SyntaxError'" -ForegroundColor White
Write-Host "  - 'ModuleNotFoundError'" -ForegroundColor White
Write-Host "  - 'odoo14_to_19_migration'" -ForegroundColor White
Write-Host ""

Write-Host "Common log locations:" -ForegroundColor Yellow
Write-Host "  - Windows Service: Check Event Viewer" -ForegroundColor White
Write-Host "  - Command line: Look at terminal output" -ForegroundColor White
Write-Host "  - Log file: Check odoo.conf for logfile setting" -ForegroundColor White
Write-Host ""

Write-Host "=== Quick Fix Steps ===" -ForegroundColor Green
Write-Host ""
Write-Host "1. FULLY STOP Odoo server" -ForegroundColor Yellow
Write-Host "2. Wait 10 seconds" -ForegroundColor Yellow
Write-Host "3. START Odoo server" -ForegroundColor Yellow
Write-Host "4. Watch startup logs for errors" -ForegroundColor Yellow
Write-Host "5. In Odoo UI: Apps > odoo14_to_19_migration > Uninstall" -ForegroundColor Yellow
Write-Host "6. Wait for uninstall" -ForegroundColor Yellow
Write-Host "7. Click Install" -ForegroundColor Yellow
Write-Host "8. Wait for install" -ForegroundColor Yellow
Write-Host "9. Test again: .\test_minimal_controller.ps1" -ForegroundColor Yellow
Write-Host ""

Write-Host "=== Verify Module Path ===" -ForegroundColor Green
Write-Host ""
Write-Host "Module should be at:" -ForegroundColor Yellow
Write-Host "  E:\odoo modules\19\metro\odoo14_to_19_migration" -ForegroundColor White
Write-Host ""
Write-Host "Check odoo.conf addons_path includes:" -ForegroundColor Yellow
Write-Host "  E:\odoo modules\19\metro" -ForegroundColor White
Write-Host ""

Write-Host "=== Test Module Import ===" -ForegroundColor Green
Write-Host ""
Write-Host "If you have Python access, test:" -ForegroundColor Yellow
Write-Host '  python -c "import sys; sys.path.insert(0, r''E:\odoo modules\19\metro''); from odoo14_to_19_migration.controllers import migration_cron_controller; print(''OK'')"' -ForegroundColor White
Write-Host ""

