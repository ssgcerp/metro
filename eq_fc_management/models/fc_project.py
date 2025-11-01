# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class ProjectFC(models.Model):
    _inherit = 'project.project'

    project_code = fields.Char(string='Project Code', readonly=True, copy=False, help='Auto-generated project code')
    is_amc = fields.Boolean(string='Is AMC Project', default=False, help='Indicates if this is an AMC project')
    
    # Stage
    stage_id = fields.Many2one('fc.project.stage', string='Stage', tracking=True, help='Project stage')
    
    # Branch Details
    branch_id = fields.Many2one('res.branch', string='Branch', help='Branch associated with this project')
    
    # Financial Tracking
    estimated_cost = fields.Monetary(string='Estimated Cost', default=0.0, currency_field='currency_id', help='Estimated project cost')
    actual_cost = fields.Monetary(string='Actual Cost', default=0.0, currency_field='currency_id', help='Actual project cost')
    cost_overrun = fields.Monetary(string='Cost Overrun', compute='_compute_cost_metrics', store=True, currency_field='currency_id', help='Difference between actual and estimated cost')
    cost_overrun_percent = fields.Float(string='Cost Overrun %', compute='_compute_cost_metrics', store=True, help='Percentage overrun of cost')
    cost_label_color = fields.Char(string='Cost Label Color', compute='_compute_cost_metrics', help='Color for cost label based on thresholds')
    
    estimated_profit = fields.Monetary(string='Estimated Profit', default=0.0, currency_field='currency_id', help='Estimated project profit')
    actual_profit = fields.Monetary(string='Actual Profit', compute='_compute_profit_metrics', store=True, currency_field='currency_id', help='Actual project profit')
    profit_percent = fields.Float(string='Profit %', compute='_compute_profit_metrics', store=True, help='Profit percentage')
    profit_label_color = fields.Char(string='Profit Label Color', compute='_compute_profit_metrics', help='Color for profit label based on thresholds')
    
    invoice_total = fields.Monetary(string='Invoice Total', default=0.0, currency_field='currency_id', help='Total invoice amount')
    invoice_paid = fields.Monetary(string='Invoice Paid', default=0.0, currency_field='currency_id', help='Total invoice amount paid')
    invoice_pending = fields.Monetary(string='Invoice Pending', compute='_compute_invoice_metrics', store=True, currency_field='currency_id', help='Pending invoice amount')
    invoice_paid_percent = fields.Float(string='Invoice Paid %', compute='_compute_invoice_metrics', store=True, help='Percentage of invoice paid')
    
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)

    @api.depends('actual_cost', 'estimated_cost')
    def _compute_cost_metrics(self):
        for record in self:
            record.cost_overrun = record.actual_cost - record.estimated_cost
            if record.estimated_cost > 0:
                record.cost_overrun_percent = (record.cost_overrun / record.estimated_cost) * 100
            else:
                record.cost_overrun_percent = 0.0
            
            # Determine label color based on thresholds
            config = self.env['fc.project.config'].get_config()
            if record.cost_overrun_percent >= config.cost_danger_threshold:
                record.cost_label_color = 'danger'  # Red
            elif record.cost_overrun_percent >= config.cost_warning_threshold:
                record.cost_label_color = 'warning'  # Orange
            else:
                record.cost_label_color = 'success'  # Green

    @api.depends('invoice_total', 'actual_cost')
    def _compute_profit_metrics(self):
        for record in self:
            record.actual_profit = record.invoice_total - record.actual_cost
            if record.invoice_total > 0:
                record.profit_percent = (record.actual_profit / record.invoice_total) * 100
            else:
                record.profit_percent = 0.0
            
            # Determine label color based on thresholds
            config = self.env['fc.project.config'].get_config()
            if record.profit_percent <= config.profit_danger_threshold:
                record.profit_label_color = 'danger'  # Red
            elif record.profit_percent <= config.profit_warning_threshold:
                record.profit_label_color = 'warning'  # Yellow/Orange
            else:
                record.profit_label_color = 'success'  # Green

    @api.depends('invoice_total', 'invoice_paid')
    def _compute_invoice_metrics(self):
        for record in self:
            record.invoice_pending = record.invoice_total - record.invoice_paid
            if record.invoice_total > 0:
                record.invoice_paid_percent = (record.invoice_paid / record.invoice_total) * 100
            else:
                record.invoice_paid_percent = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Set default stage if not provided and generate project code on stage confirmation"""
        # vals_list is already a list in Odoo 19
        # Use sudo to bypass all access checks during creation
        return super(ProjectFC, self.sudo()).create(vals_list)

    def write(self, vals):
        """Generate project code when stage changes to awarded/confirmed"""
        result = super(ProjectFC, self).write(vals)
        
        # Check if stage changed to awarded/confirmed stage
        if 'stage_id' in vals:
            for project in self:
                if not project.project_code:
                    stage = self.env['fc.project.stage'].browse(vals['stage_id'])
                    if stage.is_confirmed_stage:
                        config = self.env['fc.project.config'].get_config()
                        project.project_code = config.generate_project_code(project.is_amc)
        
        return result

    @api.model
    def _set_default_stage_for_existing_projects(self):
        """Set default stage for existing projects that don't have a stage"""
        projects_without_stage = self.search([('stage_id', '=', False)])
        if projects_without_stage:
            default_stage = self.env['fc.project.stage'].search([('sequence', '=', 10), ('active', '=', True)], limit=1)
            if default_stage:
                projects_without_stage.write({'stage_id': default_stage.id})
                return True
        return False

    @api.constrains('invoice_paid')
    def _check_invoice_paid(self):
        """Ensure invoice paid doesn't exceed invoice total"""
        for record in self:
            if record.invoice_paid > record.invoice_total:
                raise UserError('Invoice paid amount cannot exceed invoice total amount.')


class ResBranch(models.Model):
    """Branch model for organizing projects by branch"""
    _name = 'res.branch'
    _description = 'Branch'

    name = fields.Char(string='Branch Name', required=True)
    code = fields.Char(string='Branch Code', help='Branch code')
    address = fields.Text(string='Address')
    active = fields.Boolean(string='Active', default=True)
