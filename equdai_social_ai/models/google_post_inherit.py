# -*- coding: utf-8 -*-

from odoo import models, fields, api

class GooglePost(models.Model):
    _inherit = 'google.post'

    def action_open_ai_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate with AI',
            'res_model': 'social.ai.generator',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_platform': 'gmb',
                'active_id': self.id,
                'active_model': 'google.post'
            }
        }
