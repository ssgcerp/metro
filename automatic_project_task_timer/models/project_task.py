# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models


class Task(models.Model):
    """Inherited 'project.task' for running the timer """
    _inherit = 'project.task'

    task_timer = fields.Boolean(string='Timer', default=False,
                                help='Activated when task configured stage')
    is_user_working = fields.Boolean(string='Is Current User Working',
                                     compute='_compute_is_user_working',
                                     help="Technical field indicating whether "
                                          "the current user is working. ")
    duration = fields.Float(string='Real Duration', store=True, copy=False,
                            readonly=False, help='Shows the duration')
    is_status_stage = fields.Boolean(string='Stage Status',
                                     help='To set the status of task at the '
                                          'initial time.')
    check_stage = fields.Many2many('project.task.type', string='Stages',
                                   compute='_compute_check_stage',
                                   help='To check the stage whether it is '
                                        'configured or not')

    def _compute_check_stage(self):
        """To check the stage whether it is configured or not"""
        for rec in self:
            rec.check_stage = self.env['timer.configuration'].search(
                [('project_id', '=', rec.project_id.id)]).mapped('stage_ids')

    @api.constrains('stage_id')
    def _task_timer(self):
        """Checks the status of timer setting and
        toggle the task timer boolean to active """
        self.write({'is_status_stage': False})
        timer_setting = self.env['ir.config_parameter'].sudo().get_param(
            'automatic_project_task_timer.timer_setting')
        if timer_setting:
            for rec in self.env['timer.configuration'].search([]):
                if self.project_id == rec.project_id:
                    if self.stage_id & rec.stage_ids:
                        self.write({'task_timer': True})
                    else:
                        self.write({'task_timer': False})

    def _compute_is_user_working(self):
        """ Checks whether the current user is working """
        for order in self:
            order.is_user_working = any(
                x.user_id == self.env.user and not x.date_end
                for x in order.timesheet_ids
            )

    @api.model
    @api.constrains('task_timer')
    def toggle_start(self):
        """The time sheet record will be created by checking all conditions"""
        time_line_obj = self.env['account.analytic.line']
        for rec in self:
            if rec.task_timer:
                rec.write({'is_user_working': True})
                time_line_obj.create({
                    'name': f"{self.env.user.name} : {rec.name}",
                    'task_id': rec.id,
                    'user_id': self.env.user.id,
                    'project_id': rec.project_id.id,
                    'date_start': datetime.now(),
                    'stage_id': rec.stage_id.id,
                })
            else:
                rec.write({'is_user_working': False})
                time_lines = time_line_obj.search(
                    [('task_id', 'in', self.ids), ('date_end', '=', False)])
                for time_line in time_lines:
                    time_line.write({'date_end': fields.Datetime.now()})
                    if time_line.date_start:
                        diff = fields.Datetime.from_string(time_line.date_end) - \
                               fields.Datetime.from_string(time_line.date_start)
                        time_line.timer_duration = round(diff.total_seconds() / 60.0, 2)
                        time_line.unit_amount = round(diff.total_seconds() / 3600, 2)
                    else:
                        time_line.unit_amount = time_line.timer_duration = 0.0

    def get_working_duration(self):
        """Get the additional duration for open times."""
        self.ensure_one()
        duration = sum(
            (datetime.now() - time.date_start).total_seconds() / 60
            for time in self.timesheet_ids.filtered(lambda t: not t.date_end)
            if isinstance(time.date_start, datetime)
        )
        return duration
