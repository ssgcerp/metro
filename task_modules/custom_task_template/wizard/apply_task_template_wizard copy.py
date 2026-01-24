# -*- coding: utf-8 -*-

from datetime import datetime
from odoo.tools.translate import _
from odoo import api, fields, models
from odoo.exceptions import UserError
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)

class ApplyTaskTemplateWizard(models.TransientModel):
    _name = 'apply.task.template.wizard'
    _description = "Apply Task Template Wizard"

    template_group_id = fields.Many2one('task.template.group', string="Template Group", required=True)
    template_sub_group_id = fields.Many2one('task.template.sub.group', string="Template Sub Group", required=True)
    project_id = fields.Many2one('project.project', string="Project", required=True)
    apply_from_date = fields.Date(string="Apply From Date", required=True)

    def _compute_next_due_date(self, current_date, repeat_interval, repeat_unit,holiday_days):
        _logger.info("current_date_due")
        _logger.info(current_date)
        if repeat_unit == 'day':
            next_due_date = current_date + timedelta(days=repeat_interval)
        elif repeat_unit == 'week':
            next_due_date = current_date + timedelta(weeks=repeat_interval)
        elif repeat_unit == 'month':
            next_due_date = current_date + timedelta(days=repeat_interval * 30)  # Approximation
        else:
            raise ValueError("Invalid repeat unit: must be 'days', 'weeks', or 'months'.")
        _logger.info("next_due_date_before")
        _logger.info(next_due_date)
        next_due_date -= timedelta(days=1)

        while next_due_date in holiday_days:
            next_due_date += timedelta(days=1)    

        _logger.info("next_due_date_after")
        _logger.info(next_due_date)
        return next_due_date
        
    def apply_template(self):
        """Apply the selected task templates to the selected project."""
        self.ensure_one()
        
        # Fetch task templates that match the selected template group & sub-group
        task_templates = self.env['task.template'].search([
            ('template_group_id', '=', self.template_group_id.id),
            ('template_sub_group_id', '=', self.template_sub_group_id.id)
        ])

        project_task_model = self.env['project.task']

        holiday_days = self._get_holiday_dates()
        for template in task_templates:
                start_date = self.apply_from_date + timedelta(days=template.number_of_days_to_start)
                _logger.info("start_date")
                _logger.info(start_date)
                due_date = self._calculate_due_date(start_date, template.due_days, holiday_days)
                _logger.info("due_date")
                _logger.info(due_date)
                repeat_until = None
                if not template.infinite_cycle and template.total_cycle:
                    temp_date = start_date
                    for _ in range(template.total_cycle):
                        temp_date = self._compute_next_due_date(temp_date, template.repeat_interval, template.repeat_unit,holiday_days)
                    repeat_until = temp_date
                task = project_task_model.create({
                    'name': template.subject,
                    'project_id': self.project_id.id,
                    'partner_id':self.project_id.partner_id.id,
                    'priority': template.priority,
                    'date_assign': start_date,
                    'date_start': start_date,
                    'date_deadline': due_date,
                    'description': template.description,
                    'user_ids': [(6, 0, self._get_assigned_users(template))],
                    'tag_ids': [(6, 0, template.tag_ids.ids)],
                    'repeat_interval': template.repeat_interval,
                    'repeat_unit': template.repeat_unit,
                    'recurring_task': bool(template.repeat_interval),
                    'repeat_type': 'forever' if template.infinite_cycle else 'until',
                    'repeat_until': repeat_until if not template.infinite_cycle else None,
                    'internal_state':'not_started'
                    # 'date_end': due_date,
                })
                task.write({'date_end': due_date})

                follower_ids = self._get_task_followers(template)
                if follower_ids:
                    task.message_subscribe(partner_ids=follower_ids)

                start_date = start_date or fields.Datetime.now()
                task.write({'date_assign': start_date})

                for checklist in template.checklist_ids:
                    sub_task = project_task_model.create({
                        'name': checklist.name,
                        'parent_id': task.id,  
                        'project_id': self.project_id.id,
                        'user_ids': [(6, 0, self._get_checklist_assigned_users(checklist))],
                        'date_start': start_date,
                        'date_end': due_date,
                        'internal_state':'not_started'
                    })
                    sub_task.write({'date_assign': start_date,'date_end': due_date})


    def _calculate_due_date(self, start_date, due_days, holiday_days):
        _logger.info("holiday_days")
        _logger.info(holiday_days)
        current_date = start_date
        days_added = 0

        while days_added < due_days:
            if current_date not in holiday_days:
                days_added += 1
            current_date += timedelta(days=1)
        
        _logger.info("current_date")
        _logger.info(current_date)

        # if due_days != 0:
        #     current_date -= timedelta(days=1)
        _logger.info("last_current_date")
        _logger.info(current_date)
        return current_date
     

    def _get_holiday_dates(self):
        holiday_days = set()
        holidays = self.env['task.holiday'].search([])

        selected_weekdays = set()
        for holiday in holidays:
            for day in holiday.select_day:
                selected_weekdays.add(day.name)

        today = fields.Date.today()
        date_range = [today + timedelta(days=i) for i in range(365)]  

        for date in date_range:
            if date.strftime('%A').lower() in selected_weekdays:
                holiday_days.add(date)

        return holiday_days
    
    def _get_assigned_users(self, template):
        users = []
        for role in template.assignee_ids:
            role_users = self.env['project.task.member'].search([('task_role_id', '=', role.id),('project_id','=',self.project_id.id)])
            users.extend(role_users.mapped('user_id.id'))
        return users

    def _get_task_followers(self, template):
        partners = []
        for role in template.follower_ids:
            role_users = self.env['project.task.member'].search([
                ('task_role_id', '=', role.id),
                ('project_id', '=', self.project_id.id)
            ])
            partners.extend(role_users.mapped('user_id.partner_id.id'))
        return partners
    
    def _get_checklist_assigned_users(self, checklist):
        users = []
        for role in checklist.role_id:
            role_users = self.env['project.task.member'].search([('task_role_id', '=', role.id),('project_id','=',self.project_id.id)])
            users.extend(role_users.mapped('user_id.id'))
        return users

