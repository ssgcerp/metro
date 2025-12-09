# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCQuotationBuilding(models.Model):
    _name = 'amc.quotation.building'
    _description = 'AMC Quotation Building'
    _rec_name = 'building_name'
    _order = 'sequence, id'

    quotation_id = fields.Many2one('amc.quotation', string='Quotation', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    building_name = fields.Char(string='Building Name', required=True)
    location = fields.Char(string='Location')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency', related='quotation_id.currency_id', store=True, readonly=True)
