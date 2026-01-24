# -*- coding: utf-8 -*-

from odoo import models, fields

class TaskTemplateSubGroup(models.Model):
    _name = 'task.template.sub.group'
    _description = 'Task Template Sub Group'

    name = fields.Char(string="Template Sub Group", required=True)
    task_template_group_id = fields.Many2one(
        'task.template.group', 
        string="Template Group", 
        required=True
    )
