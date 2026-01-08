# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProjectMemberAllocation(models.Model):
    _name = 'project.member.allocation'
    _description = 'Project Member Allocation'
    _order = 'id desc'

    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Member', required=True)
    role_id = fields.Char(string='Role', help="Role in the project (e.g. Project Manager, Engineer)")
    allocation_percent = fields.Float(string='Allocation (%)', default=100.0)
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        # Auto-add follower to project if not already
        res = super(ProjectMemberAllocation, self).create(vals)
        if res.user_id and res.project_id:
            res.project_id.message_subscribe(partner_ids=[res.user_id.partner_id.id])
        return res
