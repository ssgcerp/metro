#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick fix script for actions with 'tree' in view_mode.
Run this in Odoo shell: python3 odoo-bin shell -d your_database_name
Then execute: exec(open('path/to/fix_view_mode.py').read())
Or copy-paste the code below into the shell.
"""

# Get the environment
env = env  # This assumes you're running in Odoo shell where 'env' is available

# Find all actions with 'tree' in view_mode
actions = env['ir.actions.act_window'].search([('view_mode', 'like', '%tree%')])

print(f"Found {len(actions)} actions with 'tree' in view_mode")

# Fix each action
for action in actions:
    if 'tree' in action.view_mode:
        # Replace 'tree' with 'list' in view_mode
        view_modes = action.view_mode.split(',')
        view_modes = ['list' if vm.strip() == 'tree' else vm.strip() for vm in view_modes]
        # Remove duplicates while preserving order
        seen = set()
        view_modes_unique = []
        for vm in view_modes:
            if vm and vm not in seen:
                seen.add(vm)
                view_modes_unique.append(vm)
        new_view_mode = ','.join(view_modes_unique)
        print(f"Action ID {action.id} ({action.name}): '{action.view_mode}' -> '{new_view_mode}'")
        action.write({'view_mode': new_view_mode})

env.cr.commit()
print("Done! All actions have been fixed.")
