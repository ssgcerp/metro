# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID
from . import models


def post_init_hook(env):
    """Fix actions with 'tree' in view_mode to use 'list' instead (Odoo 19 compatibility)"""
    # In Odoo 19, post_init_hook receives env directly
    actions = env['ir.actions.act_window'].search([('view_mode', 'like', '%tree%')])
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
            action.write({'view_mode': ','.join(view_modes_unique)})
    env.cr.commit()



