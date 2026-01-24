-- ========================================================================
-- CRITICAL: RUN THIS SQL IMMEDIATELY TO FIX THE ERROR
-- ========================================================================
-- The error "column res_company.branch_code does not exist" 
-- will be resolved after running this command.
-- ========================================================================

ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);

-- ========================================================================
-- HOW TO RUN:
-- ========================================================================
-- 1. Open pgAdmin
-- 2. Connect to PostgreSQL server
-- 3. Right-click on database "metro1" (or your database name)
-- 4. Select "Query Tool"
-- 5. Paste the SQL command above
-- 6. Click "Execute" (or press F5)
-- 7. You should see: "ALTER TABLE" (success message)
-- 8. CLOSE pgAdmin
-- 9. RESTART your Odoo server completely
-- 10. Refresh your browser
-- ========================================================================
-- 
-- The module will work perfectly after this!
-- The Branch Code field will appear in Company Settings automatically.
--
-- ========================================================================






