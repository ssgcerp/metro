# -*- coding: utf-8 -*-

from odoo import models, fields, api

class QuotationLinePreview(models.TransientModel):
    _name = 'odoo14.quotation.line.preview'
    _description = 'Odoo 14 Quotation Line Preview'
    _order = 'sequence, id'

    preview_id = fields.Many2one(
        'odoo14.quotation.preview',
        string='Quotation Preview',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(string='Sequence', default=10)
    product_name = fields.Char(string='Product', readonly=True)
    name = fields.Text(string='Description', readonly=True)
    product_uom_qty = fields.Float(string='Quantity', readonly=True)
    product_uom = fields.Char(string='UoM', readonly=True)
    price_unit = fields.Float(string='Unit Price', readonly=True)
    discount = fields.Float(string='Discount (%)', readonly=True)
    price_subtotal = fields.Float(string='Subtotal', readonly=True)
    tax_id = fields.Char(string='Taxes', readonly=True)

