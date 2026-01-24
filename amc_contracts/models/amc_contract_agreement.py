# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractAgreement(models.Model):
    _name = 'amc.contract.agreement'
    _description = 'AMC Contract Agreement'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    agreement_type = fields.Selection([
        ('standard', 'Standard Agreement'),
        ('custom', 'Custom Agreement'),
    ], string='Agreement Type', default='standard')
    agreement_text = fields.Html(string='Agreement Text', help='Full agreement text')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    signed_date = fields.Date(string='Signed Date')
    signed_by = fields.Char(string='Signed By')
    notes = fields.Text(string='Notes')






