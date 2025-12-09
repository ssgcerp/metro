from odoo import models, fields, api

class ProjectDashboard(models.Model):
    _inherit = 'project.project'

    show_next_button = fields.Boolean(compute='_compute_button_visibility')
    show_confirm_button = fields.Boolean(compute='_compute_button_visibility')
    show_cancel_button = fields.Boolean(compute='_compute_button_visibility')
    show_start_button = fields.Boolean(compute='_compute_button_visibility')
    show_complete_button = fields.Boolean(compute='_compute_button_visibility')

    @api.depends('stage_id')
    def _compute_button_visibility(self):
        for rec in self:
            stage = rec.stage_id

            if not stage:
                rec.show_next_button = False
                rec.show_confirm_button = False
                rec.show_cancel_button = False
                rec.show_start_button = False
                rec.show_complete_button = False
                continue

            rec.show_next_button     = stage.allow_next_button
            rec.show_confirm_button  = stage.allow_confirm_button
            rec.show_cancel_button   = stage.allow_cancel_button
            rec.show_start_button    = stage.confirmed_stage and not stage.completed_stage
            rec.show_complete_button = stage.completed_stage
