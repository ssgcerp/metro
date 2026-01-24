# Quick Start Guide - Migration Cron URL

## ⚠️ IMPORTANT: Module Must Be Upgraded First!

The controller won't work until you upgrade the module.

## Step 1: Upgrade Module

1. Open Odoo
2. Go to **Apps** menu
3. Remove "Apps" filter (click "Apps" in top left)
4. Search for: **odoo14_to_19_migration**
5. Click **Upgrade** button
6. Wait for upgrade to complete

## Step 2: Restart Odoo (Recommended)

After upgrading, restart Odoo server to ensure controllers are loaded.

## Step 3: Test the URL

### Test in Browser:
```
http://localhost:8079/migration/process_one?db=metrodb
```

### Test with PowerShell:
```powershell
cd "E:\odoo modules\19\metro\odoo14_to_19_migration\tools"
.\migrate_one.ps1
```

### Test with curl:
```bash
curl "http://localhost:8079/migration/process_one?db=metrodb"
```

## Expected Response

If working correctly, you should see:
```
Total Queued: 1000
Migrating Now: S00061
DONE
```

## Troubleshooting

### Still getting 404?

1. **Check module is upgraded:**
   - Apps → Search "odoo14_to_19_migration"
   - Should show "Upgrade" button if not upgraded

2. **Check Odoo logs:**
   - Look for errors about controller loading
   - Check if `controllers` module is imported

3. **Verify database name:**
   - Make sure `metrodb` is correct
   - Check in Odoo: Settings → Database → Database Manager

4. **Restart Odoo:**
   - Controllers are loaded at startup
   - Restart ensures new routes are registered

### Getting "Database not specified" error?

Make sure you include `?db=metrodb` in the URL:
```
http://localhost:8079/migration/process_one?db=metrodb
```

### Getting "Database not found" error?

- Verify database name is correct
- Check database exists in Odoo
- Try accessing Odoo web interface first to confirm database name

