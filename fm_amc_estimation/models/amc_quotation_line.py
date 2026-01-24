# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCQuotationLine(models.Model):
    _name = 'amc.quotation.line'
    _description = 'AMC Quotation Line'
    _rec_name = 'description'
    _order = 'sequence, id'

    quotation_id = fields.Many2one('amc.quotation', string='Quotation', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Html(string='Description', required=True, help='Line item description with rich text formatting')
    quantity = fields.Float(string='Quantity', default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', help='Unit of Measure')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id', default=0.0, digits='Product Price')
    subtotal = fields.Monetary(string='Subtotal', currency_field='currency_id', compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='quotation_id.currency_id', store=True, readonly=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        """Compute subtotal"""
        for line in self:
            line.subtotal = line.quantity * line.unit_price
