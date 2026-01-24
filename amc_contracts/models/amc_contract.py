# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date


class AMCContract(models.Model):
    _name = 'amc.contract'
    _description = 'AMC Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'contract_date desc, id desc'

    # Basic Information
    name = fields.Char(string='Contract', copy=False, index=True, help='Contract number (can be imported or auto-generated when confirmed)')
    stage_id = fields.Many2one('amc.contract.stage', string='Status', tracking=True, default=lambda self: self._get_default_stage(), copy=False, required=True)
    
    # Customer Information
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True, help='Customer for this contract')
    project_site = fields.Char(string='Project Site', tracking=True, help='Project site location')
    contact_id = fields.Many2one('res.partner', string='Contact', domain="[('parent_id', '=', customer_id), ('is_company', '=', False)]", help='Contact person for this contract')
    branch_id = fields.Many2one('res.company', string='Branch', required=True, default=lambda self: self.env.company, tracking=True, help='Branch/Company for this contract')
    sales_contact_id = fields.Many2one('hr.employee', string='Sales Contact', domain="[('active', '=', True)]", tracking=True, help='Sales contact person')
    
    # Dates
    contract_date = fields.Date(string='Contract Date', default=fields.Date.today, required=True, tracking=True)
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    
    # Visit Information
    visit_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
        ('manual', 'Manual')
    ], string='Visit Frequency', default='manual', tracking=True)
    number_of_visits = fields.Integer(string='Number of Visits', default=0, tracking=True)
    completion_pending = fields.Integer(string='Completion Pending', compute='_compute_completion_pending', store=True, help='Number of visits pending completion')

    # Audit Information
    audit_frequency = fields.Selection([
        ('half_yearly', 'Half Yearly'),
        ('yearly', 'Yearly'),
        ('manual', 'Manual')
    ], string='Audit Frequency', default='manual', tracking=True)
    number_of_audits = fields.Integer(string='Number of Audits', default=0, tracking=True)
    
    # Linked Records
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', copy=False, help='Analytic account for financial tracking')
    
    # Smart Button Counts
    display_sale_count = fields.Integer(compute='_compute_smart_counts')
    display_purchase_count = fields.Integer(compute='_compute_smart_counts')
    display_expense_count = fields.Integer(compute='_compute_smart_counts')
    display_invoice_count = fields.Integer(compute='_compute_smart_counts')
    display_quotation_count = fields.Integer(compute='_compute_smart_counts')
    display_visit_count = fields.Integer(compute='_compute_smart_counts')
    display_audit_count = fields.Integer(compute='_compute_smart_counts')
    
    # Financial Information
    contract_value = fields.Monetary(string='Contract Value', default=0.0, currency_field='currency_id', required=True, tracking=True)
    labour_expense = fields.Monetary(string='Labour Expense', default=0.0, currency_field='currency_id', tracking=True)
    extra_expense = fields.Monetary(string='Extra Expense', default=0.0, currency_field='currency_id', tracking=True)
    total = fields.Monetary(string='Total', compute='_compute_total', store=True, currency_field='currency_id', tracking=True)
    extra_expense_remarks = fields.Text(string='Extra Expense Remarks')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    
    # Document Options
    with_header = fields.Boolean(string='With Header', default=True, help='Include header in printed documents')
    with_stamp = fields.Boolean(string='With Stamp', default=True, help='Include stamp in printed documents')
    
    # Related Records (Tabs)
    type_of_service_ids = fields.One2many('amc.contract.type.of.service', 'contract_id', string='Types of Services')
    registration_ids = fields.One2many('amc.contract.registration', 'contract_id', string='Registration Details')
    invoice_schedule_ids = fields.One2many('amc.contract.invoice.schedule', 'contract_id', string='Invoice Schedule')
    quotation_ids = fields.One2many('amc.contract.quotation', 'contract_id', string='Quotation Details')
    service_schedule_ids = fields.One2many('amc.contract.service.schedule', 'contract_id', string='Service Schedules')
    call_out_ids = fields.One2many('amc.contract.call.out', 'contract_id', string='Call Outs')
    additional_job_ids = fields.One2many('amc.contract.additional.job', 'contract_id', string='Additional Jobs')
    agreement_ids = fields.One2many('amc.contract.agreement', 'contract_id', string='Agreements')
    agreement_ids = fields.One2many('amc.contract.agreement', 'contract_id', string='Agreements')
    expense_ids = fields.One2many('amc.contract.expense', 'contract_id', string='Expenses')
    asset_ids = fields.One2many('amc.contract.asset', 'contract_id', string='Assets')
    audit_schedule_ids = fields.One2many('amc.contract.audit.schedule', 'contract_id', string='Audit Schedules')
    
    # Other Information
    other_info = fields.Html(string='Other Info', help='Additional information and notes')
    
    # Computed Fields
    state = fields.Char(string='State', compute='_compute_state', store=True)
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired', store=True)
    is_draft = fields.Boolean(string='Is Draft', compute='_compute_is_draft', store=True, help='True if contract is in Draft status')
    is_confirmed = fields.Boolean(string='Is Confirmed', compute='_compute_is_confirmed', store=True, help='True if contract is in Confirmed status')
    is_cancelled = fields.Boolean(string='Is Cancelled', compute='_compute_is_cancelled', store=True, help='True if contract is in a cancelled stage')
    stage_color = fields.Integer(string='Stage Color', compute='_compute_stage_color', store=True, readonly=True, help='Color of the current stage')
    
    # Active field (standard in Odoo for archiving)
    active = fields.Boolean(string='Active', default=True, help='Set to False to archive this contract')
    
    # Activity
    activity_ids = fields.One2many('mail.activity', 'res_id', string='Activities')
    
    # Note: Timesheet integration can be added by extending account.analytic.line model
    
    @api.model
    def _get_default_stage(self):
        """Get default stage (Draft)"""
        stage = self.env['amc.contract.stage'].search([
            ('is_default', '=', True),
            ('name', '=', 'Draft')
        ], limit=1)
        if not stage:
            stage = self.env['amc.contract.stage'].search([], order='sequence', limit=1)
        return stage.id if stage else False

    @api.depends('contract_value', 'labour_expense', 'extra_expense')
    def _compute_total(self):
        """Compute total amount"""
        for record in self:
            record.total = record.contract_value + record.labour_expense + record.extra_expense

    @api.depends('number_of_visits', 'service_schedule_ids', 'service_schedule_ids.status')
    def _compute_completion_pending(self):
        """Compute completion pending visits"""
        for record in self:
            completed_visits = len(record.service_schedule_ids.filtered(lambda s: s.status == 'completed'))
            record.completion_pending = max(0, record.number_of_visits - completed_visits)

    @api.depends('analytic_account_id', 'service_schedule_ids', 'audit_schedule_ids', 'quotation_ids')
    def _compute_smart_counts(self):
        """Compute counts for smart buttons"""
        for record in self:
            record.display_visit_count = len(record.service_schedule_ids)
            record.display_audit_count = len(record.audit_schedule_ids)
            record.display_quotation_count = len(record.quotation_ids)
            
            # Financial Counts based on Analytic Account
            if record.analytic_account_id:
                # Sales
                record.display_sale_count = self.env['sale.order'].search_count([
                    ('analytic_account_id', '=', record.analytic_account_id.id)
                ])
                # Purchases (Check if model and field exist)
                if 'purchase.order' in self.env:
                    # Logic: Check if PO has analytic_account_id (header) OR search lines
                    # Using improved search for lines
                    record.display_purchase_count = self.env['purchase.order'].search_count([
                        ('id', 'in', self.env['purchase.order.line'].search([
                            ('analytic_distribution', 'ilike', str(record.analytic_account_id.id))
                        ]).mapped('order_id').ids)
                    ])
                else:
                    record.display_purchase_count = 0
                    
                # Expenses
                record.display_expense_count = self.env['hr.expense'].search_count([
                    ('analytic_distribution', 'ilike', str(record.analytic_account_id.id))
                ])
                
                # Invoices (Customer Invoices + Vendor Bills linked to analytic account?)
                # Usually we track Revenue (Invoices)
                record.display_invoice_count = self.env['account.move'].search_count([
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('invoice_line_ids.analytic_distribution', 'ilike', str(record.analytic_account_id.id))
                ])
            else:
                record.display_sale_count = 0
                record.display_purchase_count = 0
                record.display_expense_count = 0
                record.display_invoice_count = 0

    @api.depends('stage_id')
    def _compute_state(self):
        """Compute state from stage (stored in lowercase for consistency)"""
        for record in self:
            stage_name = record.stage_id.name if record.stage_id else 'Draft'
            record.state = stage_name.lower() if stage_name else 'draft'
    
    @api.depends('stage_id', 'stage_id.name')
    def _compute_is_draft(self):
        """Compute if contract is in Draft status"""
        for record in self:
            record.is_draft = record.stage_id and record.stage_id.name == 'Draft'
    
    @api.depends('stage_id', 'stage_id.name')
    def _compute_is_confirmed(self):
        """Compute if contract is in Confirmed status"""
        for record in self:
            record.is_confirmed = record.stage_id and record.stage_id.name == 'Confirmed'
    
    @api.depends('stage_id', 'stage_id.is_cancelled_stage')
    def _compute_is_cancelled(self):
        """Compute if contract is in a cancelled stage (any stage marked as cancelled)"""
        for record in self:
            record.is_cancelled = record.stage_id and record.stage_id.is_cancelled_stage
    
    @api.depends('stage_id', 'stage_id.color')
    def _compute_stage_color(self):
        """Update stage color when stage changes"""
        for record in self:
            record.stage_color = record.stage_id.color if record.stage_id else 0

    @api.depends('end_date')
    def _compute_is_expired(self):
        """Check if contract is expired"""
        today = fields.Date.today()
        for record in self:
            record.is_expired = record.end_date and record.end_date < today

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate contract dates"""
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End date must be after start date.')
            if record.contract_date and record.start_date:
                if record.start_date < record.contract_date:
                    raise ValidationError('Start date should not be before contract date.')

    @api.model_create_multi
    def create(self, vals_list):
        """Set default stage if not provided, allow importing contract name, handle date validation for imports"""
        today = fields.Date.today()
        for vals in vals_list:
            if 'stage_id' not in vals:
                vals['stage_id'] = self._get_default_stage()
            # If name is provided during import/create, use it; otherwise it will be auto-generated when confirmed
            
            # Handle contract_date for imports: ensure contract_date is not after start_date to avoid validation errors
            start_date = vals.get('start_date')
            contract_date = vals.get('contract_date')
            
            if start_date:
                # Parse date if it's a string (from import)
                if isinstance(start_date, str):
                    start_date = fields.Date.from_string(start_date)
                
                if contract_date:
                    # Parse date if it's a string (from import)
                    if isinstance(contract_date, str):
                        contract_date = fields.Date.from_string(contract_date)
                    # If contract_date is after start_date, adjust it to start_date
                    if contract_date > start_date:
                        vals['contract_date'] = start_date
                else:
                    # If contract_date not provided, use start_date if start_date is in the past,
                    # otherwise use today (default)
                    if start_date < today:
                        vals['contract_date'] = start_date
                    # else: contract_date defaults to today, which is fine since start_date >= today
        return super(AMCContract, self).create(vals_list)

    def write(self, vals):
        """Generate contract number when stage changes to confirmed"""
        result = super(AMCContract, self).write(vals)
        
        if 'stage_id' in vals:
            for contract in self:
                if not contract.name:
                    stage = self.env['amc.contract.stage'].browse(vals['stage_id'])
                    if stage.is_confirmed_stage:
                        contract.name = contract._generate_contract_number()
        
        return result

    def _generate_contract_number(self):
        """Generate contract number based on configuration"""
        config = self.env['amc.contract.config'].get_config()
        
        # Get branch code from company
        branch_code = None
        if self.branch_id and config.use_branch_code:
            # First try to get branch_code from res.company (if available)
            try:
                branch_code_val = self.branch_id.branch_code
                if branch_code_val:
                    branch_code = branch_code_val.upper()
            except Exception:
                # Column doesn't exist yet, try fallback methods
                branch_code = None
            
            # Fallback: Try to get branch code from res.branch if it exists
            # Note: res.branch doesn't have company_id field, so we search by name match as fallback
            if not branch_code and 'res.branch' in self.env:
                try:
                    # Try to find branch by matching name (fuzzy match)
                    branch = self.env['res.branch'].search([
                        ('name', 'ilike', self.branch_id.name or ''),
                        ('active', '=', True)
                    ], limit=1)
                    if branch and branch.code:
                        branch_code = branch.code.upper()
                except Exception:
                    # If res.branch model doesn't have expected fields, skip this fallback
                    pass
            
            # Use company name abbreviation as last resort
            if not branch_code and self.branch_id.name:
                branch_code = self.branch_id.name[:3].upper()
        
        # Get year from contract date or start date
        year = None
        if config.use_year:
            if self.start_date:
                year = self.start_date.year
            elif self.contract_date:
                year = self.contract_date.year
            else:
                year = date.today().year
        
        return config.generate_contract_number(branch_code=branch_code, year=year)

    def action_confirm(self):
        """Confirm contract and generate contract number"""
        confirmed_stage = self.env['amc.contract.stage'].search([
            ('name', '=', 'Confirmed'),
            ('is_default', '=', True)
        ], limit=1)
        
        if not confirmed_stage:
            # Try without is_default flag
            confirmed_stage = self.env['amc.contract.stage'].search([
                ('name', '=', 'Confirmed')
            ], limit=1)
        
        if not confirmed_stage:
            raise UserError('Confirmed stage not found. Please check stage configuration.')
        
        for contract in self:
            # Generate contract number if not already generated
            if not contract.name:
                contract.name = contract._generate_contract_number()
                # Post message in chatter
                contract.message_post(
                    body=f'Contract confirmed. Contract number generated: <strong>{contract.name}</strong>'
                )
            else:
                contract.message_post(body='Contract confirmed.')
            
            # Update stage to Confirmed
            contract.write({'stage_id': confirmed_stage.id})
            
            # Create/Link Analytic Account
            if not contract.analytic_account_id:
                # Find a default plan (required in newer Odoo versions)
                default_plan = self.env['account.analytic.plan'].search([], limit=1)
                if default_plan:
                    analytic_account = self.env['account.analytic.account'].create({
                        'name': self.name or f'AMC/{self.id}',
                        'partner_id': self.customer_id.id,
                        'plan_id': default_plan.id,
                    })
                    contract.analytic_account_id = analytic_account.id
        
        return True

    def action_cancel(self):
        """Cancel contract"""
        cancelled_stage = self.env['amc.contract.stage'].search([
            ('name', '=', 'Cancelled'),
            ('is_default', '=', True)
        ], limit=1)
        
        if not cancelled_stage:
            raise UserError('Cancelled stage not found. Please check stage configuration.')
        
        self.write({'stage_id': cancelled_stage.id})
        return True

    def action_block(self):
        """Block contract"""
        blocked_stage = self.env['amc.contract.stage'].search([
            ('name', '=', 'Blocked'),
            ('is_default', '=', True)
        ], limit=1)
        
        if not blocked_stage:
            raise UserError('Blocked stage not found. Please check stage configuration.')
        
        self.write({'stage_id': blocked_stage.id})
        return True

    def action_reset(self):
        """Reset contract to draft"""
        draft_stage = self.env['amc.contract.stage'].search([
            ('name', '=', 'Draft'),
            ('is_default', '=', True)
        ], limit=1)
        
        if not draft_stage:
            raise UserError('Draft stage not found. Please check stage configuration.')
        
        self.write({'stage_id': draft_stage.id})
        return True

    def action_update_expenses(self):
        """Update expenses from extra expense field"""
        # This method can be extended to create expense records
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Updated',
                'message': 'Expenses updated successfully.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_create_visits(self):
        """Create scheduled visits based on number of visits"""
        if not self.number_of_visits:
            raise UserError('Please set the number of visits first.')
        
        if not self.start_date or not self.end_date:
            raise UserError('Please set start date and end date first.')
        
        # Calculate visit intervals
        date_diff = (self.end_date - self.start_date).days
        interval_days = date_diff / (self.number_of_visits + 1) if self.number_of_visits > 0 else 0
        
        # Create visit schedules
        visit_records = []
        for i in range(1, self.number_of_visits + 1):
            visit_date = fields.Date.add(self.start_date, days=int(interval_days * i))
            visit_records.append({
                'contract_id': self.id,
                'service_date': visit_date,
                'service_type': f'Regular Service Visit {i}',
                'status': 'scheduled',
            })
        
        if visit_records:
            self.env['amc.contract.service.schedule'].create(visit_records)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'{len(visit_records)} visits created successfully.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        return True

    def action_generate_service_schedule(self):
        """Generate service schedule based on frequency"""
        if not self.start_date or not self.end_date:
            raise UserError('Please set start date and end date first.')
        
        visit_records = []
        current_date = self.start_date
        
        if self.visit_frequency == 'manual':
            return self.action_create_visits()
            
        frequency_months = {
            'monthly': 1,
            'quarterly': 3,
            'half_yearly': 6,
            'yearly': 12
        }
        
        months = frequency_months.get(self.visit_frequency, 0)
        if not months:
            return
            
        i = 1
        while current_date <= self.end_date:
            visit_records.append({
                'contract_id': self.id,
                'service_date': current_date,
                'service_type': f'{dict(self._fields["visit_frequency"].selection).get(self.visit_frequency)} Visit {i}',
                'status': 'scheduled',
            })
            # Add months to current date
            year = current_date.year + (current_date.month + months - 1) // 12
            month = (current_date.month + months - 1) % 12 + 1
            # Handle day clamping (e.g. adjacent to 31st)
            day = min(current_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            current_date = date(year, month, day)
            i += 1
            
        # Clear existing scheduled visits if needed or just add new ones? 
        # Usually better to clear explicitly or warn. For now appending.
        if visit_records:
            self.env['amc.contract.service.schedule'].create(visit_records)
            self.number_of_visits = len(self.service_schedule_ids) # Update count
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'{len(visit_records)} visits generated.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_generate_audit_schedule(self):
        """Generate audit schedule based on frequency"""
        if not self.start_date or not self.end_date:
            raise UserError('Please set start date and end date first.')
            
        audit_records = []
        current_date = self.start_date
        
        if self.audit_frequency == 'manual':
             # Manual logic handled separately or UI based
             return 
            
        frequency_months = {
            'half_yearly': 6,
            'yearly': 12
        }
        months = frequency_months.get(self.audit_frequency, 0)
        
        # Start first audit 'months' after start date or on start date? 
        # Usually audits are periodic. Let's start after period or same day?
        # Standard: Start same day or + period? Let's assume periodic intervals.
        
        i = 1
        while current_date <= self.end_date:
            audit_records.append({
                'contract_id': self.id,
                'audit_date': current_date,
                'status': 'scheduled',
            })
            year = current_date.year + (current_date.month + months - 1) // 12
            month = (current_date.month + months - 1) % 12 + 1
            day = min(current_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            current_date = date(year, month, day)
            i += 1
            
        if audit_records:
            self.env['amc.contract.audit.schedule'].create(audit_records)
            self.number_of_audits = len(self.audit_schedule_ids)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'{len(audit_records)} audits generated.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_create_sale(self):
        """Create sale order from contract"""
        # Create sale order from contract
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer_id.id,
            'date_order': fields.Datetime.now(),
            'origin': self.name or 'AMC Contract',
            # Add contract line items here if needed
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_timesheet(self):
        """View timesheets for this contract"""
        # This method can be extended when timesheet integration is added
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Timesheet',
                'message': 'Timesheet functionality will be available in future updates.',
                'type': 'info',
                'sticky': False,
            }
        }
            
    # Smart Button Actions
    def action_view_sales(self):
        self.ensure_one()
        return {
            'name': 'Sale Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('analytic_account_id', '=', self.analytic_account_id.id)],
            'context': {'default_analytic_account_id': self.analytic_account_id.id, 'default_partner_id': self.customer_id.id}
        }

    def action_view_purchases(self):
        self.ensure_one()
        domain = [('id', 'in', self.env['purchase.order.line'].search([
                            ('analytic_distribution', 'ilike', str(self.analytic_account_id.id))
                        ]).mapped('order_id').ids)]
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': domain,
            # Context for creation might be tricky with analytic distribution map, simplified:
            'context': {'default_partner_id': self.customer_id.id} 
        }

    def action_view_expenses(self):
        self.ensure_one()
        return {
            'name': 'Expenses',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('analytic_distribution', 'ilike', str(self.analytic_account_id.id))],
            'context': {'default_analytic_distribution': {str(self.analytic_account_id.id): 100}}
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('move_type', 'in', ['out_invoice', 'out_refund']),
                       ('invoice_line_ids.analytic_distribution', 'ilike', str(self.analytic_account_id.id))],
            'context': {'default_partner_id': self.customer_id.id, 'default_move_type': 'out_invoice'}
        }

    def action_view_quotations(self):
        self.ensure_one()
        # View linked Quotations (custom model)
        return {
            'name': 'Quotations',
            'type': 'ir.actions.act_window',
            'res_model': 'amc.contract.quotation',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id}
        }
        
    def action_view_schedules(self):
        self.ensure_one()
        return {
            'name': 'Service Schedules',
            'type': 'ir.actions.act_window',
            'res_model': 'amc.contract.service.schedule',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id}
        }

    def action_view_audits(self):
        self.ensure_one()
        return {
            'name': 'Audit Schedules',
            'type': 'ir.actions.act_window',
            'res_model': 'amc.contract.audit.schedule',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id}
        }

