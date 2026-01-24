from odoo import models, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.depends('project_code', 'name')
    def _compute_display_name(self):
        for project in self:
            if project.project_code and project.project_code != 'DRAFT':
                project.display_name = f"[{project.project_code}] {project.name}"
            else:
                project.display_name = project.name
