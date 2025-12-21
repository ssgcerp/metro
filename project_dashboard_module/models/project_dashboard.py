# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    # Dashboard related fields
    is_amc_project = fields.Boolean(string='Is AMC Project', default=False)
    name_of_tasks = fields.Char(string='Name of the tasks', default='Tasks')
    
    # One2many relationships for dashboard tabs
    estimation_sales_line_ids = fields.One2many(
        'project.estimation.sales.line',
        'project_id',
        string='Estimation Sales Lines'
    )
    consumable_line_ids = fields.One2many(
        'project.consumable.line',
        'project_id',
        string='Consumables'
    )
    delivery_indent_ids = fields.One2many(
        'project.delivery.indent',
        'project_id',
        string='Delivery Indents'
    )
    inventory_return_ids = fields.One2many(
        'project.inventory.return',
        'project_id',
        string='Inventory Returns'
    )
    cheque_detail_ids = fields.One2many(
        'project.cheque.detail',
        'project_id',
        string='Cheque Details'
    )
    
    # Description field for Description tab
    dashboard_description = fields.Html(string='Description', help='Project description and details')





