# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractServiceSchedule(models.Model):
    _name = 'amc.contract.service.schedule'
    _description = 'AMC Contract Service Schedule'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    service_date = fields.Date(string='Service Date', required=True)
    service_type = fields.Char(string='Service Type')
    technician_id = fields.Many2one('hr.employee', string='Technician', help='Assigned technician')
    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled')
    notes = fields.Text(string='Notes')
    sequence = fields.Integer(string='Sequence', default=10)

    _order = 'service_date, sequence'






