# -*- coding: utf-8 -*-
"""
Quick fix for view_mode 'tree' issue.
Copy and paste this entire code into Odoo shell.

To access Odoo shell:
1. Open terminal/command prompt
2. Navigate to your Odoo installation directory
3. Run: python odoo-bin shell -d livedb
   (or: "C:\Program Files\Odoo 19\python\python.exe" odoo-bin shell -d livedb)
4. Once in shell, paste this entire code block
"""

# Fix code to paste in Odoo shell:
env = env
actions = env['ir.actions.act_window'].search([('view_mode', 'like', '%tree%')])
print(f"Found {len(actions)} actions with 'tree' in view_mode")
for action in actions:
    if 'tree' in action.view_mode:
        view_modes = action.view_mode.split(',')
        view_modes = ['list' if vm.strip() == 'tree' else vm.strip() for vm in view_modes]
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
print(f"Done! Fixed {len(actions)} actions.")
