# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def action_open_project_dashboard(self):
        """Open project dashboard action"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'project_dashboard',
            'name': 'Project Dashboard',
            'context': {
                'project_id': self.id,
                'project_name': self.name,
            },
            'target': 'current',
        }
    
    def _get_form_view_id(self, view_id=None):
        """Override to add dashboard button to form view"""
        result = super()._get_form_view_id(view_id)
        # Add dashboard button via Python if view inheritance doesn't work
        return result


class ProjectDashboardHelper(models.Model):
    _name = 'project.dashboard.helper'
    _description = 'Project Dashboard Helper'

    @api.model
    def get_project_dashboard_values(self, project_id):
        """
        Compute and return dashboard values for a project.
        
        :param project_id: ID of the project
        :return: Dictionary with dashboard KPIs and chart data
        """
        project = self.env['project.project'].browse(project_id)
        if not project.exists():
            raise UserError("Project not found")
        
        # Get project stage name
        stage_name = project.stage_id.name if project.stage_id else "No Stage"
        
        # Compute invoice totals
        invoice_total, invoice_paid, invoice_pending = self._compute_invoice_totals(project)
        
        # Get estimated cost from project
        estimated_cost = project.estimated_cost or 0.0
        
        # Compute actual cost from analytic entries
        actual_cost = self._compute_actual_cost(project)
        
        # Compute estimated profit
        estimated_profit = project.estimated_profit or 0.0
        
        # Compute actual profit (invoice_total - actual_cost)
        actual_profit = invoice_total - actual_cost
        
        # Compute profit percentage
        profit_percentage = 0.0
        if estimated_cost > 0:
            profit_percentage = (actual_profit / estimated_cost) * 100 if estimated_cost > 0 else 0.0
        
        # Compute cost overrun
        cost_overrun = actual_cost - estimated_cost
        cost_overrun_pct = 0.0
        if estimated_cost > 0:
            cost_overrun_pct = (cost_overrun / estimated_cost) * 100
        
        # Chart data for invoices (Pie chart)
        chart_invoice_labels = ["Paid", "Pending"]
        chart_invoice_values = [invoice_paid, invoice_pending]
        
        # Chart data for costs (Bar chart)
        chart_cost_labels = ["Actual Cost", "Estimated Cost"]
        chart_cost_values = [actual_cost, estimated_cost]
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "stage_name": stage_name,
            "invoice_total": round(invoice_total, 2),
            "invoice_paid": round(invoice_paid, 2),
            "invoice_pending": round(invoice_pending, 2),
            "estimated_cost": round(estimated_cost, 2),
            "actual_cost": round(actual_cost, 2),
            "estimated_profit": round(estimated_profit, 2),
            "actual_profit": round(actual_profit, 2),
            "profit_percentage": round(profit_percentage, 2),
            "cost_overrun": round(cost_overrun, 2),
            "cost_overrun_pct": round(cost_overrun_pct, 2),
            "chart_invoice_labels": chart_invoice_labels,
            "chart_invoice_values": chart_invoice_values,
            "chart_cost_labels": chart_cost_labels,
            "chart_cost_values": chart_cost_values,
        }
    
    def _compute_invoice_totals(self, project):
        """
        Compute invoice totals for the project.
        
        :param project: project.project record
        :return: tuple (total, paid, pending)
        """
        # Get invoices linked to project through sale orders or analytic account
        domain = []
        analytic_account = project.analytic_account_id
        
        if analytic_account:
            # Find invoices with analytic account
            invoices = self.env['account.move'].search([
                ('line_ids.analytic_distribution', 'like', str(analytic_account.id)),
                ('state', '!=', 'cancel'),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
            ])
        else:
            # Fallback: try to find through sale orders
            sale_orders = self.env['sale.order'].search([
                ('project_id', '=', project.id)
            ])
            invoice_ids = sale_orders.mapped('invoice_ids').ids
            invoices = self.env['account.move'].browse(invoice_ids).filtered(
                lambda inv: inv.state != 'cancel' and inv.move_type in ['out_invoice', 'out_refund']
            )
        
        invoice_total = sum(invoices.mapped('amount_total'))
        invoice_paid = sum(invoices.filtered(lambda inv: inv.payment_state == 'paid').mapped('amount_total'))
        invoice_pending = invoice_total - invoice_paid
        
        return invoice_total, invoice_paid, invoice_pending
    
    def _compute_actual_cost(self, project):
        """
        Compute actual cost from analytic entries, purchases, and expenses.
        
        :param project: project.project record
        :return: total actual cost
        """
        total_cost = 0.0
        analytic_account = project.analytic_account_id
        
        if analytic_account:
            # Get costs from analytic account lines
            analytic_lines = self.env['account.analytic.line'].search([
                ('account_id', '=', analytic_account.id),
                ('amount', '<', 0),  # Negative amounts are costs
            ])
            total_cost += abs(sum(analytic_lines.mapped('amount')))
            
            # Get purchase order costs
            purchase_orders = self.env['purchase.order'].search([
                ('order_line.account_analytic_id', '=', analytic_account.id),
                ('state', 'in', ['purchase', 'done']),
            ])
            for po in purchase_orders:
                for line in po.order_line:
                    if line.account_analytic_id == analytic_account:
                        total_cost += line.price_subtotal
            
            # Get expense costs
            expenses = self.env['hr.expense'].search([
                ('analytic_distribution', 'like', str(analytic_account.id)),
                ('state', 'in', ['approved', 'done']),
            ])
            total_cost += sum(expenses.mapped('total_amount'))
        
        return total_cost

