# ✅ Branch Code Feature Enabled

## What Was Done:
1. ✅ Uncommented `branch_code` field in `res_company.py`
2. ✅ Enabled branch_code access in `amc_contract.py`
3. ✅ Added view back to manifest
4. ✅ Re-enabled post_init_hook

## ⚠️ IMPORTANT: Add Database Column

You need to add the `branch_code` column to your database. Choose ONE option:

---

## Option 1: Run SQL Manually (Recommended - Fastest)

**Run this SQL in PostgreSQL:**

```sql
ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);
```

**Steps:**
1. Open pgAdmin (or any PostgreSQL client)
2. Connect to database `metro1`
3. Open Query Tool
4. Paste the SQL above
5. Click Execute (F5)
6. **Upgrade the module in Odoo** (see below)

---

## Option 2: Let Module Upgrade Do It (Automatic)

The `post_init_hook` will automatically create the column when you upgrade:

1. **Go to Odoo Apps menu**
2. **Remove app filter** (if applied)
3. **Find "AMC Contracts Management"**
4. **Click "Upgrade"**

The hook will automatically create the column.

---

## After Adding Column:

1. **Restart Odoo server** (if you ran SQL manually)
2. **Refresh browser**
3. **Go to Settings → Companies → Your Company**
4. You'll see the **"Branch Code"** field
5. Enter your branch code (e.g., AUH, DXB, SHJ, FUJ)

---

## How It Works:

- The Branch Code field appears in **Company Settings**
- When creating AMC contracts, the branch code from the selected company/branch will be used in contract number generation
- Format example: `MFS/AMC/AUH/0001/2025` (where AUH is the branch code)

---

**Note:** If you get an error after upgrading, the column might not have been created. Run Option 1 (SQL manually) to be sure.






