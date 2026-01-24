# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractCallOut(models.Model):
    _name = 'amc.contract.call.out'
    _description = 'AMC Contract Call Out'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    call_date = fields.Datetime(string='Call Date', required=True)
    reported_by = fields.Char(string='Reported By')
    issue_description = fields.Text(string='Issue Description', required=True)
    technician_id = fields.Many2one('hr.employee', string='Assigned Technician')
    resolution_date = fields.Datetime(string='Resolution Date')
    status = fields.Selection([
        ('reported', 'Reported'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='reported')
    resolution_notes = fields.Text(string='Resolution Notes')
    sequence = fields.Integer(string='Sequence', default=10)

    _order = 'call_date desc, sequence'






