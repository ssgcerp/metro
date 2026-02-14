from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    soa_enable_auto_email = fields.Boolean(related='company_id.soa_enable_auto_email', readonly=False)
    soa_day_of_month = fields.Integer(related='company_id.soa_day_of_month', readonly=False)
    soa_statement_type = fields.Selection(related='company_id.soa_statement_type', readonly=False)
