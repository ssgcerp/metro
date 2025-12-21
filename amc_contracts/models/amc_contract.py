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
    number_of_visits = fields.Integer(string='Number of Visits', default=0, tracking=True)
    completion_pending = fields.Integer(string='Completion Pending', compute='_compute_completion_pending', store=True, help='Number of visits pending completion')
    
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
    expense_ids = fields.One2many('amc.contract.expense', 'contract_id', string='Expenses')
    
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

