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
        # next_due_date -= timedelta(days=1)

        while next_due_date in holiday_days:
            next_due_date += timedelta(days=1)    

        _logger.info("next_due_date_after")
        _logger.info(next_due_date)
        return next_due_date
        
    def apply_template(self):
        self.ensure_one()

        task_templates = self.env['task.template'].search([
            ('template_group_id', '=', self.template_group_id.id),
            ('template_sub_group_id', '=', self.template_sub_group_id.id)
        ])

        project_task_model = self.env['project.task']
        holiday_days = self._get_holiday_dates()

        for template in task_templates:
            start_date = self.apply_from_date + timedelta(days=template.number_of_days_to_start)
            due_date = self._calculate_due_date(start_date, template.due_days, holiday_days)

            repeat_until = None
            if not template.infinite_cycle and template.total_cycle:
                temp_date = start_date
                for _ in range(template.total_cycle):
                    temp_date = self._compute_next_due_date(temp_date, template.repeat_interval, template.repeat_unit, holiday_days)
                repeat_until = temp_date

            task_creation_dates = [start_date]

            # If multiple_entries is set (integer), create tasks that many times
            if template.multiple_entries and template.multiple_entries > 1 and template.repeat_interval:
                temp_start_date = start_date
                for _ in range(template.multiple_entries - 1):  # Already added 1st entry
                    temp_start_date = self._compute_next_due_date(temp_start_date, template.repeat_interval, template.repeat_unit, holiday_days)
                    task_creation_dates.append(temp_start_date)

            for task_start_date in task_creation_dates:
                task_due_date = self._calculate_due_date(task_start_date, template.due_days, holiday_days)

                task_vals = {
                    'name': template.subject,
                    'project_id': self.project_id.id,
                    'partner_id': self.project_id.partner_id.id,
                    'priority': template.priority,
                    'date_assign': task_start_date,
                    'date_start': task_start_date,
                    'date_deadline': task_due_date,
                    'description': template.description,
                    'user_ids': [(6, 0, self._get_assigned_users(template))],
                    'tag_ids': [(6, 0, template.tag_ids.ids)],
                    'internal_state': 'not_started'
                }

                if not template.multiple_entries:
                    task_vals.update({
                        'repeat_interval': template.repeat_interval,
                        'repeat_unit': template.repeat_unit,
                        'recurring_task': bool(template.repeat_interval),
                        'repeat_type': 'forever' if template.infinite_cycle else 'until',
                        'repeat_until': repeat_until if not template.infinite_cycle else None,
                    })

                task = project_task_model.create(task_vals)
                task.write({'date_end': task_due_date})

                follower_ids = self._get_task_followers(template)
                if follower_ids:
                    task.message_subscribe(partner_ids=follower_ids)

                task.write({'date_assign': task_start_date})

                # Create subtasks for checklist items
                for checklist in template.checklist_ids:
                    sub_task = project_task_model.create({
                        'name': checklist.name,
                        'parent_id': task.id,
                        'project_id': self.project_id.id,
                        'user_ids': [(6, 0, self._get_checklist_assigned_users(checklist))],
                        'date_start': task_start_date,
                        'date_end': task_due_date,
                        'internal_state': 'not_started'
                    })
                    sub_task.write({'date_assign': task_start_date, 'date_end': task_due_date})

    def _calculate_due_date(self, start_date, due_days, holiday_days):
        _logger.info("holiday_days")
        _logger.info(holiday_days)
        current_date = start_date
        days_added = 0

        while days_added < due_days:
            if current_date not in holiday_days:
                days_added += 1
            current_date += timedelta(days=1)
        
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

