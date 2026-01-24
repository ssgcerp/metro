
# -*- coding: utf-8 -*-
from odoo import models, fields

class TaskHoliday(models.Model):
    _name = 'task.holiday'
    _description = 'Task Holiday'

    name = fields.Char(string="Holiday Name", required=True)
    select_day = fields.Many2many('task.holiday.day', 'holiday_day_rel', 'day_id', 'holiday_id', 'Select Days')


class TaskHolidayDay(models.Model):
    _name = 'task.holiday.day'
    _description = 'Holiday Day'
    _rec_name = 'name'

    name = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string="Day Name", required=True)

