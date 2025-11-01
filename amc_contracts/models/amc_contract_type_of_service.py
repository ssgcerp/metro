# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractTypeOfService(models.Model):
    _name = 'amc.contract.type.of.service'
    _description = 'AMC Contract Type of Service'
    _rec_name = 'name'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    name = fields.Char(string='Service Name', required=True, help='Name of the service type')
    number = fields.Integer(string='Number', default=1, required=True, help='Number of times per year')
    times = fields.Char(string='Times', default='Times in Year', help='Time period description')
    sequence = fields.Integer(string='Sequence', default=10)

    _order = 'sequence, id'






