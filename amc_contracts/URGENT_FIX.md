# URGENT FIX: Add branch_code Column

## The Error
```
ERROR: column res_company.branch_code does not exist
```

## Immediate Solution

**Run this SQL command in your PostgreSQL database:**

```sql
ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);
```

### How to Run SQL:

#### Option A: Using pgAdmin
1. Open pgAdmin
2. Connect to your PostgreSQL server
3. Expand: Servers → PostgreSQL → Databases → **metro1** (or your database name)
4. Right-click on **metro1** → Query Tool
5. Paste the SQL command above
6. Click Execute (F5)
7. **Restart Odoo server**

#### Option B: Using psql Command Line
```bash
psql -U odoo -d metro1 -c "ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);"
```
Then **restart Odoo server**

#### Option C: Using Odoo Shell
1. Stop Odoo server
2. Run: `python odoo-bin shell -d metro1`
3. Then type:
```python
cr = env.cr
cr.execute("ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10)")
env.cr.commit()
exit()
```
4. **Restart Odoo server**

## After Running SQL
1. **Restart Odoo server completely**
2. Refresh your browser
3. The error should be gone

## Verification
After running the SQL, verify it worked:
```sql
SELECT column_name FROM information_schema.columns WHERE table_name='res_company' AND column_name='branch_code';
```
This should return one row if successful.






