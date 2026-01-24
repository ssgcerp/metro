# STEP-BY-STEP FIX FOR THE ERROR

## The Problem
The database column `branch_code` doesn't exist, causing "Internal Server Error"

## The Solution (Takes 2 minutes)

### Step 1: Run SQL Command
1. **Open pgAdmin** (PostgreSQL administration tool)
   - If you don't have it, you can use command line or any PostgreSQL client

2. **Connect to your database**
   - Database name: `metro1` (or whatever your Odoo database is called)
   - Default user: `odoo` 
   - Default password: `odoo` (or your password)

3. **Open Query Tool**
   - Right-click on the database name → **Query Tool**

4. **Run this SQL command:**
   ```sql
   ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);
   ```

5. **Click Execute** (or press F5)

6. **You should see**: "ALTER TABLE" - success message

### Step 2: Restart Odoo
1. **Stop Odoo server completely**
2. **Start Odoo server again**
3. **Refresh your browser**

### Step 3: Enable the View (if needed)
If the Branch Code field doesn't appear in Company Settings:
1. Open `__manifest__.py`
2. Find line 71 and uncomment (remove #):
   ```python
   'views/res_company_views.xml',
   ```
3. Update the module

## Alternative: Command Line Method

If you prefer command line:

```bash
cd "C:\Program Files\PostgreSQL\12\bin"
psql -U odoo -d metro1 -c "ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);"
```

Enter password when prompted, then restart Odoo.

---

**After completing these steps, the error will be gone and everything will work!**






