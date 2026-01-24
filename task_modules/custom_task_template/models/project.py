from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    def action_apply_task_stage(self):
        all_stages = self.env['project.task.type'].search([])
        for stage in all_stages:
            stage.project_ids = [(4, self.id)]  

    def action_apply_task_timer(self):
        in_progress = self.env['project.task.type'].search([('name', '=', 'In Progress')], limit=1)
        re_work = self.env['project.task.type'].search([('name', '=', 'Re work')], limit=1)
        stage_ids = [s.id for s in [in_progress, re_work] if s]

        if stage_ids:
            self.env['timer.configuration'].create({
                'project_id': self.id,
                'stage_ids': [(6, 0, stage_ids)]
            })
