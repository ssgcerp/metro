# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrderAMCExtend(models.Model):
    """Extend sale.order to add a direct AMC Contract link."""
    _inherit = 'sale.order'

    amc_contract_id = fields.Many2one(
        'amc.contract',
        string='AMC Contract',
        tracking=True,
        domain="[('customer_id', '=', partner_id), ('active', '=', True)]",
        help='Link this sale order directly to an AMC Contract',
    )

    @api.onchange('partner_id')
    def _onchange_partner_clear_amc(self):
        """Clear AMC contract when customer changes."""
        if self.amc_contract_id and self.amc_contract_id.customer_id != self.partner_id:
            self.amc_contract_id = False

    @api.onchange('amc_contract_id')
    def _onchange_amc_contract_id(self):
        """When AMC contract selected, auto-fill customer if not set."""
        if self.amc_contract_id and not self.partner_id:
            self.partner_id = self.amc_contract_id.customer_id

    def _prepare_invoice(self):
        """Pass AMC contract and project to the generated invoice."""
        invoice_vals = super(SaleOrderAMCExtend, self)._prepare_invoice()
        
        # Pass AMC Contract if set
        if self.amc_contract_id:
            invoice_vals['amc_contract_id'] = self.amc_contract_id.id
            
        # Pass Project if set (project_id added by fm_amc_crm_custom)
        if hasattr(self, 'project_id') and self.project_id:
            invoice_vals['project_id'] = self.project_id.id
            
        return invoice_vals
