# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractExpense(models.Model):
    _name = 'amc.contract.expense'
    _description = 'AMC Contract Expense'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    expense_date = fields.Date(string='Expense Date', required=True)
    expense_type = fields.Selection([
        ('labour', 'Labour'),
        ('material', 'Material'),
        ('travel', 'Travel'),
        ('other', 'Other'),
    ], string='Expense Type', required=True)
    description = fields.Text(string='Description', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='contract_id.currency_id', store=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    account_move_id = fields.Many2one('account.move', string='Journal Entry')
    sequence = fields.Integer(string='Sequence', default=10)

    _order = 'expense_date desc, sequence'






