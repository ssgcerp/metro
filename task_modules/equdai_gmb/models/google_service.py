# -*- coding: utf-8 -*-

from odoo import models, fields, api

class GoogleService(models.Model):
    _name = 'google.service'
    _description = 'Google Business Service'

    name = fields.Char(string='Service Name', required=True)
    profile_id = fields.Many2one('google.business.profile', string='Location', required=True, ondelete='cascade')
    
    price = fields.Monetary(string='Price')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    description = fields.Text(string='Description')
