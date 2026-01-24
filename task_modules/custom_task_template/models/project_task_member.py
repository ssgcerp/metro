# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectTaskMember(models.Model):
    _name = 'project.task.member'
    _description = 'Project Task Member'

    project_id = fields.Many2one('project.project', string="Project", required=True)
    user_id = fields.Many2one('res.users', string="Employee", required=True)
    task_role_id = fields.Many2one('task.role', string="Role", required=True)

class Project(models.Model):
    _inherit = 'project.project'

    task_member_ids = fields.One2many('project.task.member', 'project_id', string="Task Members")
    social_media_ids = fields.One2many('project.social.media', 'project_id', string="Social Media Accounts")
    project_type_id = fields.Many2one('project.type', string='Project Type')
