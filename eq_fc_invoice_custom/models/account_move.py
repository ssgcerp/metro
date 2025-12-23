# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    """Extend account.move (Customer Invoices) with custom fields"""
    _inherit = 'account.move'

    # Custom fields for customer invoices
    location = fields.Char(string='Location', help="Location information")
    site_name = fields.Char(string='Site Name', help="Site name for the invoice")
    create_do = fields.Boolean(string='Create DO', default=False, help="Create Delivery Order")
    bank_details = fields.Text(string='Bank Details', help="Bank details information")
    file_to_upload = fields.Binary(string='File', help="File to upload")
    filename = fields.Char(string='Filename', help="Name of the uploaded file")
    in_note = fields.Text(string='Invoice Note', help="Additional notes for the invoice")
    
    # AMC Contract - Selection field filtered by customer
    # Using Many2one which appears as a selection dropdown in the UI
    amc_contract_id = fields.Many2one(
        'amc.contract',
        string='AMC Contract',
        domain="[('customer_id', '=', partner_id)]",
        help="AMC Contract for this customer. Only contracts for the selected customer are shown."
    )
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Clear AMC Contract when customer changes"""
        self.amc_contract_id = False

