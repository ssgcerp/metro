# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractQuotation(models.Model):
    _name = 'amc.contract.quotation'
    _description = 'AMC Contract Quotation Details'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    quotation_number = fields.Char(string='Quotation Number')
    quotation_date = fields.Date(string='Quotation Date')
    quotation_amount = fields.Monetary(string='Quotation Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='contract_id.currency_id', store=True, readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', help='Link to sale order')
    notes = fields.Text(string='Notes')
    sequence = fields.Integer(string='Sequence', default=10)

    _order = 'sequence, id'






