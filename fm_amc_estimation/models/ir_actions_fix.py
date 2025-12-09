# -*- coding: utf-8 -*-

from odoo import models, api


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    @api.model
    def _fix_view_mode_tree(self):
        """Fix actions with 'tree' in view_mode to use 'list' instead (Odoo 19 compatibility)"""
        actions = self.search([('view_mode', 'like', '%tree%')])
        for action in actions:
            if 'tree' in action.view_mode:
                # Replace 'tree' with 'list' in view_mode
                new_view_mode = action.view_mode.replace('tree', 'list')
                # Remove any duplicate 'list' entries
                view_modes = new_view_mode.split(',')
                view_modes = list(dict.fromkeys(view_modes))  # Remove duplicates while preserving order
                action.write({'view_mode': ','.join(view_modes)})
        return True
