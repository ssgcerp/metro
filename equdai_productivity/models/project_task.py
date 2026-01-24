# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta

class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_blocked = fields.Boolean(string="Is Blocked", default=False, tracking=True)
    blocker_type = fields.Selection([
        ('client', 'Client Feedback'),
        ('manager', 'Manager Approval'),
        ('technical', 'Technical Issue'),
        ('other', 'Other')
    ], string="Blocker Type", tracking=True)
    blocker_reason = fields.Char(string="Blocker Reason", tracking=True)
    blocked_date = fields.Datetime(string="Blocked Since", readonly=True)

    def action_set_blocked(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Block Task',
            'res_model': 'project.task.block.wizard', # Or use a simple write if we don't want a wizard yet
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id}
        }
    
    # Simplified version without wizard for now
    def action_toggle_block(self):
        for task in self:
            if task.is_blocked:
                task.write({
                    'is_blocked': False,
                    'blocker_type': False,
                    'blocker_reason': False,
                    'blocked_date': False
                })
            else:
                task.write({
                    'is_blocked': True,
                    'blocked_date': fields.Datetime.now()
                })

    @api.model
    def _cron_check_blocked_tasks(self):
        """ Checks for tasks blocked for more than 24 hours and notifies """
        threshold = fields.Datetime.now() - timedelta(hours=24)
        stale_tasks = self.search([
            ('is_blocked', '=', True), 
            ('blocked_date', '<', threshold)
        ])
        
        for task in stale_tasks:
            # Create an activity for the project manager or task assignee
            user_id = task.user_ids[:1].id if task.user_ids else self.env.user.id
            if task.project_id.user_id:
                user_id = task.project_id.user_id.id

            task.activity_schedule(
                'mail.mail_activity_data_warning',
                user_id=user_id,
                note=f"Task '{task.name}' has been blocked for over 24 hours due to {task.blocker_type}: {task.blocker_reason}. Please investigate."
            )
