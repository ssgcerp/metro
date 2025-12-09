# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class InvoiceLinePreview(models.TransientModel):
    _name = 'odoo14.invoice.line.preview'
    _description = 'Odoo 14 Invoice Line Preview'
    _order = 'sequence, id'

    invoice_preview_id = fields.Many2one('odoo14.invoice.preview', string='Invoice', required=True, ondelete='cascade')
    product_name = fields.Char(string='Product', readonly=True)
    name = fields.Text(string='Description', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    price_unit = fields.Float(string='Unit Price', readonly=True)
    discount = fields.Float(string='Discount (%)', readonly=True)
    tax_names = fields.Char(string='Taxes', readonly=True)
    price_subtotal = fields.Float(string='Subtotal', readonly=True)
    sequence = fields.Integer(string='Sequence', readonly=True, default=10)

