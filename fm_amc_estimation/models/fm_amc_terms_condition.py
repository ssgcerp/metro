# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FMAMCTermsCondition(models.Model):
    _name = 'fm.amc.terms.condition'
    _description = 'AMC Terms and Condition'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Name', required=True, help='Name of the terms and condition')
    description = fields.Html(string='Description', help='Terms and conditions description with rich text formatting')
    active = fields.Boolean(string='Active', default=True, help='If unchecked, it will allow you to hide the terms and condition without removing it.')
