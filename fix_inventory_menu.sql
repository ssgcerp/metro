-- SQL Script to check and fix Inventory menu visibility
-- Run this in pgAdmin Query Tool on your Odoo database
-- NOTE: Odoo 19 uses JSONB for menu names, so we need special syntax

-- Step 1: Check if stock module is installed
SELECT name, state, latest_version 
FROM ir_module_module 
WHERE name = 'stock';

-- Step 2: Find Inventory menu by XML ID (most reliable method)
-- The Inventory menu usually has XML ID: stock.menu_stock_root
SELECT m.id, m.name, m.active, m.sequence, m.parent_id, m.web_icon, d.name as xml_id
FROM ir_ui_menu m
INNER JOIN ir_model_data d ON d.res_id = m.id
WHERE d.module = 'stock' 
AND d.name = 'menu_stock_root';

-- Step 3: Activate Inventory menu if it's inactive (using XML ID)
UPDATE ir_ui_menu 
SET active = true 
FROM ir_model_data d
WHERE ir_ui_menu.id = d.res_id
AND d.module = 'stock' 
AND d.name = 'menu_stock_root';

-- Step 4: Check Stock User and Manager groups
SELECT id, name 
FROM res_groups 
WHERE name IN ('Stock / User', 'Stock / Manager');

-- Step 5: Check current user's groups (replace USER_ID with your user ID)
-- First, find your user ID:
SELECT id, login, name 
FROM res_users 
WHERE login = 'your_email@example.com';  -- Replace with your login email

-- Then check groups for that user (replace USER_ID):
SELECT g.id, g.name
FROM res_groups g
INNER JOIN res_groups_users_rel rel ON g.id = rel.gid
WHERE rel.uid = USER_ID;  -- Replace USER_ID with your actual user ID

-- Step 6: Add Stock / User group to a user (replace USER_ID and GROUP_ID)
-- First get the Stock / User group ID:
SELECT id FROM res_groups WHERE name = 'Stock / User';

-- Then add it to user (replace USER_ID and GROUP_ID):
-- Example: If Stock/User group ID is 50 and your user ID is 2:
-- INSERT INTO res_groups_users_rel (gid, uid) VALUES (50, 2)
-- ON CONFLICT DO NOTHING;

-- Step 7: Verify menu is visible (using XML ID)
SELECT m.id, m.name, m.active, m.sequence, d.name as xml_id
FROM ir_ui_menu m
INNER JOIN ir_model_data d ON d.res_id = m.id
WHERE d.module = 'stock' 
AND d.name = 'menu_stock_root';
