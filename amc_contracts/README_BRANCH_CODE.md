# Quick Fix for Branch Code Column Error

If you're getting the error:
```
ERROR: column res_company.branch_code does not exist
```

## Option 1: Update the Module (Recommended)
1. Go to Apps menu
2. Remove the app filter (if applied)
3. Find "AMC Contracts Management" module
4. Click "Upgrade"

This will automatically create the column.

## Option 2: Manual SQL Fix (Quick)
Connect to your PostgreSQL database and run:

```sql
ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);
```

**Steps:**
1. Open pgAdmin or any PostgreSQL client
2. Connect to your Odoo database (e.g., `metro1`)
3. Open Query Tool
4. Run the SQL above
5. Refresh your Odoo browser

## After Fix
Once the column is created, restart Odoo server or refresh your browser. The error should be resolved.






