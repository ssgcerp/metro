# 🔧 FIX 404 ERROR - Step by Step Guide

## The Problem
Getting `404 Not Found - No database is selected and the requested URL was not found in the server-wide controllers`

This means the route `/migration/process_one` is **NOT registered** in Odoo yet.

## ✅ SOLUTION - Follow These Steps EXACTLY:

### Step 1: Verify Module Files Are Correct ✅
The files are already correct:
- ✅ `controllers/migration_cron_controller.py` exists
- ✅ `controllers/__init__.py` imports the controller
- ✅ `__init__.py` imports controllers
- ✅ Route uses `auth='none'` for server-wide access

### Step 2: **UPGRADE THE MODULE** (CRITICAL!)
1. Open Odoo in browser: `http://localhost:8079`
2. Go to **Apps** menu
3. **Remove the "Apps" filter** (click "Apps" in top left to show all modules)
4. Search for: **`odoo14_to_19_migration`**
5. Click the **"Upgrade"** button
6. Wait for upgrade to complete (you'll see a success message)

### Step 3: **RESTART ODOO SERVER** (REQUIRED!)
Controllers are loaded when Odoo starts. After upgrading:
1. **Stop** the Odoo server completely
2. **Start** the Odoo server again
3. Wait for it to fully start (check logs)

### Step 4: Test the Route
Run the diagnostic script:
```powershell
cd "E:\odoo modules\19\metro\odoo14_to_19_migration\tools"
.\diagnose_route.ps1
```

Or test manually:
```powershell
.\migrate_one.ps1
```

## 🔍 If Still Not Working:

### Check Odoo Logs
Look in `C:\Program Files\Odoo 19\server\odoo.log` for:
- Errors about importing `odoo14_to_19_migration.controllers`
- Any Python syntax errors
- Module loading errors

### Verify Module is Installed
1. Go to Apps → Search `odoo14_to_19_migration`
2. Should show **"Installed"** status (not "Not Installed")
3. If not installed, click **"Install"** first, then **"Upgrade"**

### Check Database Name
Make sure `metrodb` is the correct database name:
1. Go to Settings → Database → Database Manager
2. Verify the exact database name
3. Update `$DATABASE` in `migrate_one.ps1` if different

### Manual Route Test
Open in browser:
```
http://localhost:8079/migration/process_one?db=metrodb
```

Should return:
```
Total Queued: X
Migrating Now: Y
DONE
```

## ⚠️ Common Mistakes:
- ❌ Forgetting to click "Upgrade" button
- ❌ Not restarting Odoo after upgrade
- ❌ Module is "Installed" but not "Upgraded"
- ❌ Wrong database name
- ❌ Odoo server not fully started

## ✅ Success Indicators:
- ✅ Module shows "Upgrade" button (means it needs upgrade)
- ✅ After upgrade, button changes to "Upgrade" (grayed out) or disappears
- ✅ Route returns status text (not 404)
- ✅ No errors in Odoo logs about controller loading

