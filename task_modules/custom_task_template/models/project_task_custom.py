
# -*- coding: utf-8 -*-
from odoo import models, fields,api
from collections import defaultdict

class ProjectTask(models.Model):
    _inherit = 'project.task'


    date_start = fields.Datetime(string="Start Date")
    date_end = fields.Datetime(string="End Date")
    has_social_media = fields.Boolean(
        compute="_compute_has_social_media",
        string="Has Social Media"
    )
    social_post_id = fields.Many2one("social.post", string="Social Post", readonly=True)
    social_post_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("posted", "Posted"),
            ("failed", "Failed")
        ],
        string="Social Post State",
        related="social_post_id.state",
        store=True,
    )
    content_type_id = fields.Many2one("task.content.type", string="Content Type")
    content_pillar_id = fields.Many2one("task.content.pillar", string="Content Pillar")
    content_topic = fields.Char(string="Content Topic")

    internal_state = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted_for_approval', 'Submitted for Approval'),
        ('in_correction', 'In Correction'),
        ('re_working', 'Re Working'),
        ('in_submit', 'In Submit'),
        ('partially_approved', 'Partially Approved'),
        ('confirmed', 'Confirmed')
    ], string="State", default="not_started", required=True,tracking=True)

   
    def action_open_subtask_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    def action_approve_social_media(self):
        for task in self:
            task.internal_state = 'partially_approved'

    def action_approve_digital_marketing(self):
        for task in self:
            task.internal_state = 'confirmed'

    
    @api.depends('project_id.social_media_ids')
    def _compute_has_social_media(self):
        for task in self:
            task.has_social_media = bool(task.project_id and task.project_id.social_media_ids)

    def action_post_on_social_media(self):
        self.ensure_one()
        
        social_accounts = self.env['project.social.media'].search([
        ('project_id', '=', self.project_id.id)
        ]).mapped('social_account_id')
        
        attachment_ids = self.env['ir.attachment'].search([
            ('res_model', '=', 'project.task'),
            ('res_id', 'in', [self.id] + self.child_ids.ids)  
        ]).ids

        return {
            'name': 'Social Post',
            'type': 'ir.actions.act_window',
            'res_model': 'social.post',
            'view_mode': 'form',
            'view_id': self.env.ref('social.social_post_view_form').id,
            'target': 'new',
            'context': {
                'default_account_ids': [(6, 0, social_accounts.ids)],
                'default_image_ids': [(6, 0, attachment_ids)],
                'default_project_id': self.project_id.id,
            },
        }
    
    def action_open_social_post(self):
        self.ensure_one()
        if self.social_post_id:
            return {
                "name": "Social Post",
                "type": "ir.actions.act_window",
                "res_model": "social.post",
                "view_id": self.env.ref('social.social_post_view_form').id,
                "view_mode": "form",
                "res_id": self.social_post_id.id,
                "target": "current",
            }
        
    def action_open_sm_calendar(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Social Media Calendar',
            'view_mode': 'calendar',
            'res_model': 'social.post',
            'domain': [('project_id', '=', self.project_id.id)],
            'context': {'default_project_id': self.project_id.id},
        }


class ProjectProject(models.Model):
    _inherit = 'project.project'


    def _compute_task_count(self):
        project_and_state_counts = self.env['project.task'].with_context(
            active_test=any(project.active for project in self)
        )._read_group(
            [('project_id', 'in', self.ids),('parent_id','=',None)],
            ['project_id', 'state'],
            ['__count'],
        )
        task_counts_per_project_id = defaultdict(lambda: {
            'open_task_count': 0,
            'closed_task_count': 0,
        })
        for project, state, count in project_and_state_counts:
            task_counts_per_project_id[project.id]['closed_task_count' if state in ('done','cancel') else 'open_task_count'] += count
        for project in self:
            open_task_count, closed_task_count = task_counts_per_project_id[project.id].values()
            project.open_task_count = open_task_count
            project.closed_task_count = closed_task_count
            project.task_count = open_task_count + closed_task_count