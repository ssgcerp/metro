# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    """Extend account.move to add AMC Contract and Project links."""
    _inherit = 'account.move'

    amc_contract_id = fields.Many2one(
        'amc.contract',
        string='AMC Contract',
        tracking=True,
        domain="[('customer_id', '=', partner_id), ('active', '=', True)]",
        help='Linked AMC Contract. Auto-populated from Sale Order if applicable.',
    )
    
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        tracking=True,
        domain="[('partner_id', '=', partner_id)]",
        help='Linked Project. Auto-populated from Sale Order if applicable.',
    )

    @api.onchange('partner_id')
    def _onchange_partner_clear_custom_fields(self):
        """Clear AMC contract and Project when the customer changes."""
        if self.amc_contract_id and self.amc_contract_id.customer_id != self.partner_id:
            self.amc_contract_id = False
        if self.project_id and self.project_id.partner_id != self.partner_id:
            self.project_id = False
