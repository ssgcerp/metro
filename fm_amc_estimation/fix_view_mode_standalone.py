#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone script to fix actions with 'tree' in view_mode.
Run: "C:\Program Files\Odoo 19\python\python.exe" fix_view_mode_standalone.py
"""

import sys
import os

# Add Odoo to path (adjust if needed)
odoo_paths = [
    r"C:\Program Files\Odoo 19",
    r"C:\Program Files\Odoo 19\server",
    r"C:\Program Files\Odoo 19\odoo",
]

for path in odoo_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)
        break

try:
    import odoo
    from odoo import api, SUPERUSER_ID
    from odoo.tools import config
    
    # Initialize Odoo
    odoo.tools.config.parse_config(['-c', r'C:\Program Files\Odoo 19\odoo.conf'])  # Adjust path if needed
    odoo.service.db.initialize()
    
    # Connect to database
    db_name = 'livedb'
    registry = odoo.registry(db_name)
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Find all actions with 'tree' in view_mode
        actions = env['ir.actions.act_window'].search([('view_mode', 'like', '%tree%')])
        
        print(f"Found {len(actions)} actions with 'tree' in view_mode")
        
        # Fix each action
        fixed_count = 0
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
                fixed_count += 1
        
        cr.commit()
        print(f"\nDone! Fixed {fixed_count} actions.")

except ImportError as e:
    print(f"Error importing Odoo: {e}")
    print("\nPlease run this script using Odoo shell instead:")
    print('1. Open terminal in Odoo installation directory')
    print('2. Run: python odoo-bin shell -d livedb')
    print('3. Then paste the code from fix_view_mode.py')
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    print("\nTrying alternative method...")
    print("Please use Odoo shell method instead (see instructions above)")
