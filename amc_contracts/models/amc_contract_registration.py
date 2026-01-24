# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractRegistration(models.Model):
    _name = 'amc.contract.registration'
    _description = 'AMC Contract Registration Details'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    registration_number = fields.Char(string='Registration Number')
    registration_date = fields.Date(string='Registration Date')
    registration_authority = fields.Char(string='Registration Authority')
    expiry_date = fields.Date(string='Expiry Date')
    notes = fields.Text(string='Notes')
    sequence = fields.Integer(string='Sequence', default=10)

    _order = 'sequence, id'






