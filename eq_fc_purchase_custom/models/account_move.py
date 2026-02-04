# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    """Extend account.move (Vendor Bills) with custom fields"""
    _inherit = 'account.move'

    # Custom fields for vendor bills
    quote_reference = fields.Char(string='Quote Reference', help="Reference to the quotation")
    lpo_number = fields.Char(string='LPO Number', help="Local Purchase Order number")
    voucher_number = fields.Char(string='Voucher Number', help="Voucher number")
    po_number = fields.Char(string='PO Number', help="Purchase Order number")
    is_wo_header = fields.Boolean(string='Invoice Without Header', default=False, help="Invoice without header")
    is_with_stamp = fields.Boolean(string='With Stamp', default=False, help="Include stamp on documents")
    
    @api.model_create_multi
    def create(self, vals_list):
        """Set PO Number from purchase_id if available"""
        for vals in vals_list:
            if 'po_number' not in vals or not vals.get('po_number'):
                if 'purchase_id' in vals and vals.get('purchase_id'):
                    purchase_order = self.env['purchase.order'].browse(vals['purchase_id'])
                    if purchase_order:
                        vals['po_number'] = purchase_order.name
        return super().create(vals_list)
    
    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        """Set PO Number when purchase order is selected"""
        if self.purchase_id:
            self.po_number = self.purchase_id.name

    @api.constrains('name', 'journal_id', 'state', 'date')
    def _constrains_date_sequence(self):
        """
        Override to allow out-of-order dates for Vendor Bills.
        Standard Odoo prevents posting a bill with an earlier date if a later bill exists in the sequence.
        We bypass this for Vendor Bills to allow flexible entry.
        """
        # Filter moves that are NOT Vendor Bills/Refunds
        moves_to_check = self.filtered(lambda m: m.move_type not in ('in_invoice', 'in_refund'))
        
        # Only call super (standard validation) for non-vendor bills
        if moves_to_check:
            super(AccountMove, moves_to_check)._constrains_date_sequence()


