# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractAdditionalJob(models.Model):
    _name = 'amc.contract.additional.job'
    _description = 'AMC Contract Additional Job'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    job_description = fields.Text(string='Job Description', required=True)
    job_date = fields.Date(string='Job Date')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='contract_id.currency_id', store=True, readonly=True)
    technician_id = fields.Many2one('hr.employee', string='Technician')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('billed', 'Billed'),
    ], string='Status', default='pending')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    notes = fields.Text(string='Notes')
    sequence = fields.Integer(string='Sequence', default=10)

    _order = 'job_date desc, sequence'






