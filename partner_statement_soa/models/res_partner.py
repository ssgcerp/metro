from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_open_partner_statement(self):
        self.ensure_one()
        return {
            'name': 'Partner Statement',
            'type': 'ir.actions.act_window',
            'res_model': 'partner.statement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_ids': [self.id],
                'default_company_id': self.env.company.id,
            }
        }
