-- SQL script to fix actions with 'tree' in view_mode
-- Run this in pgAdmin Query Tool on database: livedb

-- Step 1: Check action 756 specifically (the one causing the error)
SELECT id, name, view_mode, res_model
FROM ir_act_window 
WHERE id = 756;

-- Step 2: Check if view_mode is stored in ir_act_window_view table
SELECT act_window_id, view_mode, view_id
FROM ir_act_window_view
WHERE act_window_id = 756;

-- Step 3: Check ALL actions with 'tree' in view_mode (in main table)
SELECT id, name, view_mode, res_model
FROM ir_act_window 
WHERE view_mode LIKE '%tree%'
ORDER BY id;

-- Step 4: Check if 'tree' exists in ir_act_window_view table
SELECT act_window_id, view_mode, view_id
FROM ir_act_window_view
WHERE view_mode LIKE '%tree%'
ORDER BY act_window_id;

-- Step 5: Fix in ir_act_window table
UPDATE ir_act_window 
SET view_mode = REPLACE(view_mode, 'tree', 'list')
WHERE view_mode LIKE '%tree%';

-- Step 6: Fix in ir_act_window_view table (if it exists)
UPDATE ir_act_window_view
SET view_mode = REPLACE(view_mode, 'tree', 'list')
WHERE view_mode LIKE '%tree%';

-- Step 7: Verify action 756 is fixed
SELECT id, name, view_mode, res_model
FROM ir_act_window 
WHERE id = 756;

SELECT act_window_id, view_mode, view_id
FROM ir_act_window_view
WHERE act_window_id = 756;

-- Step 8: Final verification - no 'tree' should remain
SELECT id, name, view_mode 
FROM ir_act_window 
WHERE view_mode LIKE '%tree%';

SELECT act_window_id, view_mode 
FROM ir_act_window_view
WHERE view_mode LIKE '%tree%';
