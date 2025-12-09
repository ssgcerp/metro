# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FMAMCContractPeriod(models.Model):
    _name = 'fm.amc.contract.period'
    _description = 'AMC Contract Period'
    _rec_name = 'name'
    _order = 'number_of_days'

    name = fields.Char(string='Name', required=True, help='Name of the contract period (e.g., One Year, Two Year, Three Year, Four Year)')
    number_of_days = fields.Integer(string='Number of Days', required=True, help='Number of days for this contract period')
    active = fields.Boolean(string='Active', default=True, help='If unchecked, it will allow you to hide the contract period without removing it.')

    _sql_constraints = [
        ('number_of_days_positive', 'CHECK(number_of_days > 0)', 'Number of days must be greater than 0!'),
        ('name_uniq', 'unique(name)', 'Contract period name must be unique!'),
    ]
