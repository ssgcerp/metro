# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCQuotationProduct(models.Model):
    _name = 'amc.quotation.product'
    _description = 'AMC Quotation Product'
    _rec_name = 'product_id'
    _order = 'sequence, id'

    quotation_id = fields.Many2one('amc.quotation', string='Quotation', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    quantity = fields.Float(string='Quantity', default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='quotation_id.currency_id', store=True, readonly=True)
