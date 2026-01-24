# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleQuotationDeclineWizard(models.TransientModel):
    _name = 'sale.quotation.decline.wizard'
    _description = 'Quotation Decline Wizard'

    order_id = fields.Many2one('sale.order', string='Quotation', required=True)
    reason = fields.Text(string='Decline Reason', required=True, help='Reason for declining this quotation')

    def action_decline(self):
        """Confirm decline and return quotation to Draft"""
        self.ensure_one()
        if not self.reason:
            raise ValidationError("Please provide a reason for declining the quotation.")
        
        # Call the reject_confirm method on the order
        self.order_id.action_reject_confirm(reason=self.reason)
        return {'type': 'ir.actions.act_window_close'}

