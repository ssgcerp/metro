# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractInvoiceSchedule(models.Model):
    _name = 'amc.contract.invoice.schedule'
    _description = 'AMC Contract Invoice Schedule'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    invoice_date = fields.Date(string='Invoice Date', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    invoice_number = fields.Char(string='Invoice Number')
    invoice_id = fields.Many2one('account.move', string='Invoice', help='Link to accounting invoice')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
    ], string='Status', default='draft')
    currency_id = fields.Many2one('res.currency', string='Currency', related='contract_id.currency_id', store=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)
    notes = fields.Text(string='Notes')

    _order = 'invoice_date, sequence'






