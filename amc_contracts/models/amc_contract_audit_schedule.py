# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AMCContractAuditSchedule(models.Model):
    _name = 'amc.contract.audit.schedule'
    _description = 'AMC Contract Audit Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'audit_date'

    contract_id = fields.Many2one('amc.contract', string='Contract', required=True, ondelete='cascade')
    audit_date = fields.Date(string='Audit Date', required=True, tracking=True)
    auditor_id = fields.Many2one('res.users', string='Auditor', tracking=True)
    
    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='scheduled', tracking=True)
    
    findings = fields.Html(string='Audit Findings')
    remarks = fields.Text(string='Remarks')
    
    active = fields.Boolean(string='Active', default=True)
