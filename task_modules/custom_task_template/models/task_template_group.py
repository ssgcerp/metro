# -*- coding: utf-8 -*-

from odoo import models, fields

class TemplateGroup(models.Model):
    _name = 'task.template.group'
    _description = 'Template Group'

    name = fields.Char(string="Template Group Name", required=True)
    enable_platform = fields.Boolean(string="Enable Platform")