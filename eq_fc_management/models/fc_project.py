# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProjectFC(models.Model):
    _inherit = 'project.project'

    project_code = fields.Char(string='Project Code', copy=False, default='DRAFT',
                               help='Auto-generated project code')
    amc_contract_id = fields.Many2one(
        'amc.contract',
        string='AMC Contract',
        help='Linked AMC contract for this project'
    )
    partner_id = fields.Many2one('res.partner', string='Customer')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    
    # Stage
    stage_id = fields.Many2one(
        'fc.project.stage',
        string='Stage',
        tracking=True,
        help='Project stage',
        group_expand='_read_group_stage_ids',
        groups=False,
    )
    # Visibility flags: not stored, default False so they render hidden until compute runs
    stage_allow_confirm = fields.Boolean(compute='_compute_stage_action_flags', string='Stage Allows Confirm', readonly=True)
    stage_allow_cancel = fields.Boolean(compute='_compute_stage_action_flags', string='Stage Allows Cancel', readonly=True)
    stage_is_confirmed_stage = fields.Boolean(compute='_compute_stage_action_flags', string='Is Confirmed Stage', readonly=True)
    stage_is_completed_stage = fields.Boolean(compute='_compute_stage_action_flags', string='Is Completed Stage', readonly=True)
    
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
    is_confirmed = fields.Boolean(string='Confirmed', default=False, tracking=True)
    is_amc = fields.Boolean(string='Is Amc', default=False, help='Indicates if this is an AMC project')
    is_amc_project = fields.Boolean(string='Is AMC Project', default=False, help='Indicates if this is an AMC project')

    # Members Allocation
    member_allocation_ids = fields.One2many('project.member.allocation', 'project_id', string='Members Allocation')

    # Smart Button Counts
    sale_count = fields.Integer(compute='_compute_smart_counts', string="Sales")
    purchase_count = fields.Integer(compute='_compute_smart_counts', string="Purchases")
    expense_count = fields.Integer(compute='_compute_smart_counts', string="Expenses")
    invoice_count = fields.Integer(compute='_compute_smart_counts', string="Invoices")
    invoice_count = fields.Integer(compute='_compute_smart_counts', string="Invoices")
    approval_count = fields.Integer(compute='_compute_smart_counts', string="Approvals")
    document_count = fields.Integer(compute='_compute_smart_counts', string="Documents")
    delivery_count = fields.Integer(compute='_compute_smart_counts', string="Deliveries")
    stock_count = fields.Integer(compute='_compute_smart_counts', string="Stocks")


    @api.onchange('partner_id', 'company_id')
    def _onchange_amc_contract(self):
        for rec in self:
            domain = [('id', '=', 0)]
            if rec.partner_id and rec.company_id:
                domain = [
                    ('customer_id', '=', rec.partner_id.id),
                    ('branch_id', '=', rec.company_id.id),
                    ('stage_id.is_confirmed_stage', '=', True),
                    ('active', '=', True),
                ]
            rec.amc_contract_id = False
            return {'domain': {'amc_contract_id': domain}}

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

    @api.depends('stage_id', 'company_id')
    def _compute_stage_action_flags(self):
        Stage = self.env['fc.project.stage'].sudo()
        for project in self:
            stage = project.stage_id
            company_id = project.company_id.id or self.env.company.id
            next_stage = project._find_next_stage(stage) if stage else Stage.browse()
            completed_stage = project._find_completed_stage(company_id) if stage else Stage.browse()
            confirmed_stage = project._find_confirmed_stage(company_id) if stage else Stage.browse()

            allow_next = bool(
                stage
                and stage.allow_next_action
                and not stage.is_confirmed_stage
                and not stage.is_cancel_stage
                and not stage.is_completed_stage
            )

            allow_start = bool(stage and stage.is_confirmed_stage)

            allow_complete = bool(
                stage
                and completed_stage
                and not stage.is_confirmed_stage
                and not stage.is_completed_stage
                and stage.id != completed_stage.id
                and (stage.sequence or 0) < (completed_stage.sequence or 0)
                and confirmed_stage
                and (stage.sequence or 0) >= (confirmed_stage.sequence or 0)
            )

            # Legacy flags retained for compatibility; visibility now controlled by _compute_button_visibility
            project.stage_allow_confirm = bool(stage and stage.allow_confirm_action)
            project.stage_allow_cancel = bool(stage and stage.allow_cancel_action)
            project.stage_is_confirmed_stage = bool(stage and stage.is_confirmed_stage)
            project.stage_is_completed_stage = bool(stage and stage.is_completed_stage)

    def _find_next_stage(self, current_stage=None):
        self.ensure_one()
        Stage = self.env['fc.project.stage'].sudo()
        stage = current_stage or self.stage_id
        if not stage:
            return Stage.browse()

        domain = [
            ('active', '=', True),
            ('sequence', '>', stage.sequence or 0),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ]
        return Stage.search(domain, order='sequence asc, id asc', limit=1)

    def _find_completed_stage(self, company_id=None):
        self.ensure_one()
        Stage = self.env['fc.project.stage'].sudo()
        company_id = company_id or self.company_id.id
        domain = [
            ('active', '=', True),
            ('is_completed_stage', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id),
        ]
        return Stage.search(domain, order='sequence asc, id asc', limit=1)

    def _find_confirmed_stage(self, company_id=None):
        self.ensure_one()
        Stage = self.env['fc.project.stage'].sudo()
        company_id = company_id or self.company_id.id
        domain = [
            ('active', '=', True),
            ('is_confirmed_stage', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id),
        ]
        return Stage.search(domain, order='sequence asc, id asc', limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        """Set default stage if not provided and generate project code on stage confirmation"""
        Stage = self.env['fc.project.stage'].sudo()
        default_stage = Stage.search([('is_draft_stage', '=', True), ('active', '=', True)], limit=1)
        if not default_stage:
            default_stage = Stage.search([('sequence', '=', 10), ('active', '=', True)], limit=1)

        prepared_vals = []
        for vals in vals_list:
            vals = dict(vals)
            if not vals.get('stage_id') and default_stage:
                vals['stage_id'] = default_stage.id
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
            prepared_vals.append(vals)

        # Use sudo to bypass all access checks during creation
        return super(ProjectFC, self.sudo()).create(prepared_vals)

    def write(self, vals):
        """Generate project code when stage changes to awarded/confirmed"""
        if 'stage_id' in vals and not self.env.context.get('allow_stage_transition'):
            requested_stage = vals.get('stage_id')
            target_stage = False
            if isinstance(requested_stage, int):
                target_stage = self.env['fc.project.stage'].browse(requested_stage)
            elif isinstance(requested_stage, (list, tuple)) and requested_stage:
                first_value = requested_stage[0]
                if isinstance(first_value, int):
                    target_stage = self.env['fc.project.stage'].browse(first_value)

            if target_stage and target_stage.is_confirmed_stage:
                raise UserError(_('Use the Confirm button to move the project into the Awarded stage.'))

            for project in self:
                current_stage = project.stage_id
                if current_stage and current_stage.is_confirmed_stage:
                    if not target_stage:
                        raise UserError(_('Projects in the Awarded stage cannot be moved back to Draft.'))
                    if target_stage.sequence < current_stage.sequence:
                        raise UserError(_('Projects in the Awarded stage cannot return to an earlier stage. Use Start Project to continue.'))

        result = super(ProjectFC, self).write(vals)
        
        # Check if stage changed to awarded/confirmed stage
        if 'stage_id' in vals and 'project_code' not in vals:
            for project in self:
                stage = project.stage_id
                updates = {}
                if stage and stage.is_confirmed_stage:
                    config = self.env['fc.project.config'].get_config()
                    if project.project_code in (False, 'DRAFT'):
                        updates['project_code'] = config.generate_project_code(
                            project=project,
                            is_amc=project._is_amc_project(),
                        )
                    if not project.is_confirmed:
                        updates['is_confirmed'] = True
                elif stage and stage.is_cancel_stage:
                    if project.is_confirmed:
                        updates['is_confirmed'] = False
                elif stage and not stage.is_confirmed_stage and project.is_confirmed:
                    updates['is_confirmed'] = False

                if updates:
                    super(ProjectFC, project.sudo()).write(updates)
        
        return result

    def action_next_stage(self):
        """Move project to the next configured stage (excluding confirmed stage)."""
        for project in self:
            stage = project.stage_id
            if not stage:
                raise UserError(_('Assign a stage before progressing.'))

            next_stage = project._find_next_stage(stage)
            if not next_stage:
                raise UserError(_('No subsequent stage configured.'))
            if next_stage.is_confirmed_stage:
                raise UserError(_('Use Confirm to move the project into the awarded stage.'))

            project.with_context(allow_stage_transition=True).sudo().write({'stage_id': next_stage.id})

        return True

    def action_confirm_project(self):
        """Move project from draft to confirmed stage and generate project code."""
        for project in self:
            confirmed_stage = self.env['fc.project.stage'].sudo().search([
                ('is_confirmed_stage', '=', True),
                ('active', '=', True),
                '|',
                ('company_id', '=', project.company_id.id),
                ('company_id', '=', False),
            ], order='sequence asc', limit=1)
            if not confirmed_stage:
                raise UserError(_('Please configure a confirmed/awarded stage in Project Stages.'))

            stage = project.stage_id
            if not stage:
                raise UserError(_('Set a project stage before confirming.'))
            if stage.id == confirmed_stage.id:
                raise UserError(_('This project is already in the awarded stage.'))
            if not (stage.allow_confirm_action or stage.is_draft_stage or (stage.sequence or 0) < (confirmed_stage.sequence or 0)):
                raise UserError(_('This stage cannot confirm a project. Please move the project to a confirmation-eligible stage first.'))

            config = self.env['fc.project.config'].get_config()
            project_code = config.generate_project_code(
                project=project,
                is_amc=project._is_amc_project(),
            )

            write_vals = {
                'stage_id': confirmed_stage.id,
                'is_confirmed': True,
            }
            if project_code:
                write_vals['project_code'] = project_code

            project.with_context(allow_stage_transition=True).sudo().write(write_vals)

        return True

    def action_cancel_project(self):
        """Move project to the configured cancelled stage."""
        Stage = self.env['fc.project.stage'].sudo()
        cancel_stage = Stage.search([
            ('is_cancel_stage', '=', True),
            ('active', '=', True),
            '|',
            ('company_id', '=', self.env.company.id),
            ('company_id', '=', False),
        ], order='sequence asc', limit=1)

        if not cancel_stage:
            raise UserError('Please configure a cancellation stage in Project Stages.')

        for project in self:
            project.with_context(allow_stage_transition=True).sudo().write({
                'stage_id': cancel_stage.id,
                'is_confirmed': False,
            })

        return True

    def action_start_project(self):
        """Advance an awarded project into the next stage (typically In Progress)."""
        for project in self:
            current_stage = project.stage_id
            if not current_stage or not current_stage.is_confirmed_stage:
                raise UserError(_('Only awarded projects can be started.'))

            next_stage = project._find_next_stage(current_stage)

            if not next_stage:
                raise UserError(_('Please configure a stage that comes after Awarded (e.g., In Progress).'))

            project.with_context(allow_stage_transition=True).sudo().write({
                'stage_id': next_stage.id,
            })

        return True

    def action_complete_project(self):
        """Move project into the configured completed stage."""
        for project in self:
            completed_stage = project._find_completed_stage()
            if not completed_stage:
                raise UserError(_('Please configure a completed stage in Project Stages.'))

            current_stage = project.stage_id
            if current_stage and current_stage.id == completed_stage.id:
                raise UserError(_('This project is already marked as completed.'))
            if current_stage and (current_stage.sequence or 0) > (completed_stage.sequence or 0):
                raise UserError(_('This project is beyond the configured completed stage.'))

            project.with_context(allow_stage_transition=True).sudo().write({
                'stage_id': completed_stage.id,
            })

        return True

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """Ensure the status bar displays all active stages for the company."""
        Stage = stages.sudo().with_context(active_test=False)
        company_id = self.env.context.get('company_id') or self.env.company.id
        search_domain = [
            ('active', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id),
        ]
        result = Stage.search(search_domain, order='sequence, id')
        return result if result else stages

    def _is_amc_project(self):
        self.ensure_one()
        return bool(self.amc_contract_id)

    def action_view_dashboard(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("project.open_view_project_all_group_stage")
        dashboard_view = self.env.ref("eq_fc_management.view_project_dashboard_form")
        action.update({
            "res_id": self.id,
            "view_mode": "form",
            "views": [(dashboard_view.id, "form")],
            "context": dict(self.env.context, form_view_ref="eq_fc_management.view_project_dashboard_form"),
            "target": "current",
        })
        return action

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
    def _compute_counts(self):
        # Override or extend existing if needed
        pass

    def _compute_smart_counts(self):
        for project in self:
            project.task_count = self.env['project.task'].search_count([('project_id', '=', project.id)])
            
            # Safe access to analytic account
            analytic_account = getattr(project, 'analytic_account_id', False)
            analytic_id = analytic_account.id if analytic_account else False
            
            if analytic_id:
                project.sale_count = self.env['sale.order'].search_count([('analytic_account_id', '=', analytic_id)])
                project.purchase_count = self.env['purchase.order'].search_count([('order_line.account_analytic_id', '=', analytic_id)]) # More robust search
                project.expense_count = self.env['hr.expense'].search_count([('analytic_account_id', '=', analytic_id)])
                # Invoices: Check invoice lines. This can be complex with distribution dicts in newer Odoo.
                # Simplified check using ilike on the distribution string representation or one2many if available
                project.invoice_count = self.env['account.move'].search_count([
                    ('move_type', 'in', ('out_invoice', 'out_refund')),
                    ('invoice_line_ids.analytic_distribution', 'ilike', str(analytic_id))
                ])
                project.approval_count = 0
                
                # Documents (Attachments)
                project.document_count = self.env['ir.attachment'].search_count([
                    ('res_model', '=', 'project.project'), ('res_id', '=', project.id)
                ])

                # Deliveries & Stocks (Linked via Sales/Purchases in Analytic Account)
                # Find Sale Orders linked to this analytic account
                sale_ids = self.env['sale.order'].search([('analytic_account_id', '=', analytic_id)]).ids
                if sale_ids:
                    project.delivery_count = self.env['stock.picking'].search_count([
                        ('sale_id', 'in', sale_ids), 
                        ('picking_type_code', '=', 'outgoing')
                    ])
                else:
                    project.delivery_count = 0
                
                # Find Purchase Orders linked to this analytic account
                # Note: Purchase linking to analytic might vary, checking order line is safer but slower
                # For count, we might rely on PO header if customized, otherwise complex query.
                # Simplified: Check POs where any line has the analytic account
                purchase_ids = self.env['purchase.order'].search([
                    ('order_line.account_analytic_id', '=', analytic_id)
                ]).ids
                if purchase_ids:
                    project.stock_count = self.env['stock.picking'].search_count([
                        ('purchase_id', 'in', purchase_ids), 
                        ('picking_type_code', '=', 'incoming')
                    ])
                else:
                    project.stock_count = 0

            else:
                # Fallback: Try linking via project_id where possible
                project.sale_count = self.env['sale.order'].search_count([('project_id', '=', project.id)]) if hasattr(self.env['sale.order'], 'project_id') else 0
                project.purchase_count = 0 
                project.expense_count = 0
                project.invoice_count = 0
                project.approval_count = 0
                project.document_count = self.env['ir.attachment'].search_count([
                    ('res_model', '=', 'project.project'), ('res_id', '=', project.id)
                ])
                project.delivery_count = 0
                project.stock_count = 0

    def action_view_sales(self):
        self.ensure_one()
        analytic_account = getattr(self, 'analytic_account_id', False)
        analytic_id = analytic_account.id if analytic_account else False
        
        domain = [('analytic_account_id', '=', analytic_id)] if analytic_id else [('project_id', '=', self.id)]
        context = {'create': False}
        if analytic_id:
             context['default_analytic_account_id'] = analytic_id
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': domain,
            'context': context
        }

    def action_view_purchases(self):
        self.ensure_one()
        analytic_account = getattr(self, 'analytic_account_id', False)
        analytic_id = analytic_account.id if analytic_account else False
        # Purchase orders often link via lines, but modern Odoo might have header field too. 
        # Checking lines is safer for analytics.
        domain = [('order_line.account_analytic_id', '=', analytic_id)] if analytic_id else [('id', '=', 0)]
        context = {'create': False}
        if analytic_id:
             context['default_analytic_account_id'] = analytic_id

        return {
             'type': 'ir.actions.act_window',
             'name': 'Purchases',
             'res_model': 'purchase.order',
             'view_mode': 'list,form',
             'domain': domain,
             'context': context
        }

    def action_view_expenses(self):
        self.ensure_one()
        analytic_account = getattr(self, 'analytic_account_id', False)
        analytic_id = analytic_account.id if analytic_account else False
        domain = [('analytic_account_id', '=', analytic_id)] if analytic_id else [('id', '=', 0)]
        
        return {
             'type': 'ir.actions.act_window',
             'name': 'Expenses',
             'res_model': 'hr.expense',
             'view_mode': 'list,form',
             'domain': domain,
             'context': {'create': False, 'default_analytic_account_id': analytic_id}
        }

    def action_view_invoices(self):
        self.ensure_one()
        analytic_account = getattr(self, 'analytic_account_id', False)
        analytic_id = analytic_account.id if analytic_account else False
        
        domain = [('move_type', 'in', ('out_invoice', 'out_refund')), ('invoice_line_ids.analytic_distribution', 'ilike', str(analytic_id))] if analytic_id else [('id', '=', 0)]

        return {
             'type': 'ir.actions.act_window',
             'name': 'Invoices',
             'res_model': 'account.move',
             'view_mode': 'list,form',
             'domain': domain,
             'context': {'create': False}
        }

    def action_view_approvals(self):
        # Placeholder
        return {'type': 'ir.actions.act_window_close'}

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'project.project'), ('res_id', '=', self.id)],
            'context': {'create': True, 'default_res_model': 'project.project', 'default_res_id': self.id}
        }

    def action_view_deliveries(self):
        self.ensure_one()
        analytic_account = getattr(self, 'analytic_account_id', False)
        analytic_id = analytic_account.id if analytic_account else False
        
        domain = [('id', '=', 0)]
        if analytic_id:
            sale_ids = self.env['sale.order'].search([('analytic_account_id', '=', analytic_id)]).ids
            if sale_ids:
                domain = [('sale_id', 'in', sale_ids), ('picking_type_code', '=', 'outgoing')]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Deliveries',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'create': False}
        }

    def action_view_stocks(self):
        self.ensure_one()
        analytic_account = getattr(self, 'analytic_account_id', False)
        analytic_id = analytic_account.id if analytic_account else False
        
        domain = [('id', '=', 0)]
        if analytic_id:
            purchase_ids = self.env['purchase.order'].search([('order_line.account_analytic_id', '=', analytic_id)]).ids
            if purchase_ids:
                domain = [('purchase_id', 'in', purchase_ids), ('picking_type_code', '=', 'incoming')]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Stocks',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'create': False}
        }

    def action_view_amc(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'amc.contract',
            'view_mode': 'form',
            'res_id': self.amc_contract_id.id,
            'target': 'current',
        }


class ResBranch(models.Model):
    """Branch model for organizing projects by branch"""
    _name = 'res.branch'
    _description = 'Branch'

    name = fields.Char(string='Branch Name', required=True)
    code = fields.Char(string='Branch Code', help='Branch code')
    address = fields.Text(string='Address')
    active = fields.Boolean(string='Active', default=True)
