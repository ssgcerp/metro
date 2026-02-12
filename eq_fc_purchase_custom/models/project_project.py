# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Project(models.Model):
    _inherit = "project.project"
    _rec_names_search = ['name', 'project_code']

    # code field removed as we use project_code from eq_fc_management

    @api.depends('name', 'project_code')
    def _compute_display_name(self):
        for project in self:
            if project.project_code and project.project_code != 'DRAFT':
                project.display_name = f"[{project.project_code}] {project.name}"
            else:
                project.display_name = project.name
