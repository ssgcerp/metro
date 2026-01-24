
# -*- coding: utf-8 -*-
from odoo import models, fields

class TaskTemplate(models.Model):
    _name = 'task.template'
    _description = 'Task Template'

    subject = fields.Char(string="Subject", required=True)
    template_group_id = fields.Many2one('task.template.group', string="Template Group", required=True)
    template_sub_group_id = fields.Many2one('task.template.sub.group', string="Template Sub Group",domain="[('task_template_group_id', '=', template_group_id)]")
    
    number_of_days_to_start = fields.Integer(string="Number of Days to Start")
    due_days = fields.Integer(string="Due Days")

    priority = fields.Selection([
    ('0', 'Low'),   
    ('1', 'High'), 
    ], string="Priority", default='0', required=True)
    # repeat_every = fields.Selection([
    #     ('week', '1 Week'),
    #     ('two_weeks', '2 Weeks'),
    #     ('one_month', '1 Month'),
    #     ('three_months', '3 Months'),
    #     ('six_months', '6 Months'),
    #     ('one_year', '1 Year'),
    #     ('custom', 'Custom')
    # ], string="Repeat Every")

    repeat_interval = fields.Integer(string="Repeat Interval")
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years')
    ])

    total_cycle = fields.Integer(string="Total Cycle", help="Number of times the task should repeat.")
    infinite_cycle = fields.Boolean(string="Repeat Forever", help="If enabled, the task will repeat indefinitely.")
    multiple_entries = fields.Integer(string="Multiple Entries", help="Number of times the task should create.")

    # custom_recurring = fields.Integer(string="Custom Recurring Number", help="Number of times the task should repeat in custom interval.")
    # custom_repeat_type = fields.Selection([
    #     ('days', 'Days'),
    #     ('weeks', 'Weeks'),
    #     ('months', 'Months'),
    #     ('years', 'Years')
    # ], string="Custom Repeat Type")

    checklist_ids = fields.One2many('task.template.checklist', 'task_template_id', string="Checklist Items")
    
    assignee_ids = fields.Many2many('task.role', 'assignee_role_rel', 'role_id', 'assignee_id', 'Assignees')
    follower_ids = fields.Many2many('task.role', 'follower_role_rel', 'role_id', 'follower_d', 'Followers')

    description = fields.Text(string="Description")

    tag_ids = fields.Many2many('project.tags', 'template_project_tag_rel', 'task_template_id','tag_id', 'Tags')

    platform = fields.Many2one('task.platform', string="Platform")
    enable_platform = fields.Boolean(related="template_group_id.enable_platform",store=True)


    def action_apply_task_template_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apply Task Template',
            'res_model': 'apply.task.template.wizard',
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
        }


class TaskTemplateChecklist(models.Model):
    _name = 'task.template.checklist'
    _description = 'Task Template Checklist'

    name = fields.Char(string="Checklist Item", required=True)
    role_id = fields.Many2one('task.role', string="Select Role")
    task_template_id = fields.Many2one('task.template', string="Task Template", ondelete="cascade")



