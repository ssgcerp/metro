@echo off
cd /d "E:\odoo modules\19\metro"
echo === Git Auto Commit and Push ===
echo.
echo Current directory:
cd
echo.
echo Adding all files...
git add -A
echo.
echo Committing changes...
git commit -m "Auto-commit: Add module analysis documentation, update estimation form layout (single column), add auto-commit scripts"
echo.
echo Pushing to remote...
git push origin main
echo.
echo === Done ===
pause

