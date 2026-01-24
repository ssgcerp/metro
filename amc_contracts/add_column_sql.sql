-- Run this SQL manually in your database to add the branch_code column
-- Connect to your Odoo database (e.g., metro1) and run:
ALTER TABLE res_company ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10);






