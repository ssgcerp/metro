# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import date


class FMAMCEstimation(models.Model):
    _name = 'fm.amc.estimation'
    _description = 'FM AMC Estimation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'estimation_date desc, id desc'

    # Basic Information
    name = fields.Char(string='Estimation Number', readonly=True, copy=False, index=True, help='Auto-generated estimation number')
    stage_id = fields.Many2one('fm.amc.estimation.stage', string='Status', tracking=True, 
                               default=lambda self: self._get_default_stage(), copy=False, required=True)
    
    # Customer Information
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True, 
                                 help='Customer for this estimation')
    contact_id = fields.Many2one('res.partner', string='Contact', 
                                 domain="[('parent_id', '=', partner_id), ('is_company', '=', False)]", 
                                 help='Contact person for this estimation')
    
    # Integration Fields
    lead_id = fields.Many2one('crm.lead', string='Lead', tracking=True,
                              help='Related CRM Lead/Opportunity',
                              domain="[('partner_id', '=', partner_id)]")
    amc_contract_id = fields.Many2one('amc.contract', string='AMC Contract', tracking=True, 
                                      help='Related AMC Contract', 
                                      domain="[('customer_id', '=', partner_id), ('active', '=', True), ('stage_id.name', 'not in', ['Draft', 'Cancelled', 'Blocked'])]")
    project_id = fields.Many2one('project.project', string='Project', tracking=True, 
                                help='Related Project',
                                domain="[('partner_id', '=', partner_id)]")
    
    # Company and Branch
    branch_id = fields.Many2one('res.company', string='Branch', required=True, 
                               default=lambda self: self.env.company, tracking=True, 
                               help='Branch/Company for this estimation')
    sales_contact_id = fields.Many2one('hr.employee', string='Sales Contact', 
                                       domain="[('active', '=', True)]", tracking=True, 
                                       help='Sales contact person')
    
    # Additional Information
    estimated_hours = fields.Float(string='Estimated Hours', default=0.0, 
                                   help='Estimated hours for this estimation')
    
    # Dates
    estimation_date = fields.Date(string='Estimation Date', default=fields.Date.today, 
                                required=True, tracking=True)
    validity_date = fields.Date(string='Validity Date', tracking=True, 
                               help='Date until which this estimation is valid')
    
    # Financial Information
    product_cost = fields.Monetary(string='Product Cost', default=0.0, currency_field='currency_id')
    installation_price = fields.Monetary(string='Installation Price', default=0.0,
                                         currency_field='currency_id', tracking=True)
    expense = fields.Monetary(string='Expense', default=0.0, currency_field='currency_id', tracking=True,
                              help='Total expense from expense lines')
    total_cost = fields.Monetary(string='Total', default=0.0, currency_field='currency_id')
    profit = fields.Monetary(string='Profit', default=0.0, currency_field='currency_id')
    price = fields.Monetary(string='Price', default=0.0, currency_field='currency_id', tracking=True)
    # Per-tab totals (without tax)
    project_amount_total = fields.Monetary(
        string='Project Estimations', compute='_compute_amounts', store=True, currency_field='currency_id'
    )
    consumable_amount_total = fields.Monetary(
        string='Consumable Estimations', compute='_compute_amounts', store=True, currency_field='currency_id'
    )
    expense_amount_total = fields.Monetary(
        string='Expense', compute='_compute_amounts', store=True, currency_field='currency_id'
    )
    travel_amount_total = fields.Monetary(
        string='Travel & Accommodation', compute='_compute_amounts', store=True, currency_field='currency_id'
    )
    amount_untaxed = fields.Monetary(string='Untaxed Amount', compute='_compute_amounts', 
                                    store=True, currency_field='currency_id')
    amount_tax = fields.Monetary(string='Tax Amount', compute='_compute_amounts', 
                                 store=True, currency_field='currency_id')
    amount_total = fields.Monetary(string='Total', compute='_compute_amounts', 
                                   store=True, currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, 
                                  default=lambda self: self.env.company.currency_id)
    
    # Estimation Lines (unified)
    line_ids = fields.One2many('fm.amc.estimation.line', 'estimation_id', 
                               string='Estimation Lines')
    
    # Separate line collections for tabs (same inverse but different domain)
    project_line_ids = fields.One2many('fm.amc.estimation.line', 'estimation_id', 
                                      string='Project Lines',
                                      domain=[('line_type', '=', 'project')])
    consumable_line_ids = fields.One2many('fm.amc.estimation.line', 'estimation_id', 
                                          string='Consumable Lines',
                                          domain=[('line_type', '=', 'consumable')])
    expense_line_ids = fields.One2many('fm.amc.estimation.line', 'estimation_id', 
                                       string='Expense Lines',
                                       domain=[('line_type', '=', 'expense')])
    travel_line_ids = fields.One2many('fm.amc.estimation.line', 'estimation_id',
                                      string='Travel & Accommodation Lines',
                                      domain=[('line_type', '=', 'travel')])
    
    # Related Quotation
    sale_order_id = fields.Many2one('sale.order', string='Created Quotation', 
                                    readonly=True, copy=False, 
                                    help='Quotation created from this estimation')
    
    # Notes
    note = fields.Html(string='Terms and Conditions', help='Internal notes and terms')
    
    # Computed Fields
    is_draft = fields.Boolean(string='Is Draft', compute='_compute_is_draft', store=True, 
                              help='True if estimation is in Draft status')
    is_waiting_approval = fields.Boolean(string='Is Waiting Approval', compute='_compute_stage_flags', 
                                        store=True, help='True if estimation is waiting for approval')
    is_approved = fields.Boolean(string='Is Approved', compute='_compute_is_approved', store=True, 
                                help='True if estimation is approved')
    is_locked = fields.Boolean(string='Is Locked', compute='_compute_is_locked', store=True, 
                              help='True if estimation is locked')
    stage_color = fields.Integer(string='Stage Color', compute='_compute_stage_color', store=True, 
                                 readonly=True, help='Color of the current stage')
    
    # Active field
    active = fields.Boolean(string='Active', default=True, help='Set to False to archive this estimation')

    @api.model
    def _get_default_stage(self):
        """Get default stage (Draft)"""
        stage = self.env['fm.amc.estimation.stage'].search([
            ('is_default', '=', True),
            ('name', '=', 'Draft')
        ], limit=1)
        if not stage:
            stage = self.env['fm.amc.estimation.stage'].search([], order='sequence', limit=1)
        return stage.id if stage else False

    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.price_total', 'line_ids.line_type', 'line_ids.display_type')
    def _compute_amounts(self):
        """Compute total amounts"""
        for estimation in self:
            # Exclude section and note lines from calculations
            regular_lines = estimation.line_ids.filtered(lambda l: not l.display_type)
            estimation.amount_untaxed = sum(regular_lines.mapped('price_subtotal'))
            estimation.amount_tax = sum(regular_lines.mapped('price_tax'))
            estimation.amount_total = sum(regular_lines.mapped('price_total'))
            
            # Compute per-tab totals (excluding section and note lines)
            estimation.project_amount_total = sum(
                estimation.line_ids.filtered(lambda l: l.line_type == 'project' and not l.display_type).mapped('price_subtotal')
            )
            estimation.consumable_amount_total = sum(
                estimation.line_ids.filtered(lambda l: l.line_type == 'consumable' and not l.display_type).mapped('price_subtotal')
            )
            estimation.expense_amount_total = sum(
                estimation.line_ids.filtered(lambda l: l.line_type == 'expense' and not l.display_type).mapped('price_subtotal')
            )
            estimation.travel_amount_total = sum(
                estimation.line_ids.filtered(lambda l: l.line_type == 'travel' and not l.display_type).mapped('price_subtotal')
            )

    @api.depends('stage_id', 'stage_id.name')
    def _compute_is_draft(self):
        """Compute if estimation is in Draft status"""
        for record in self:
            record.is_draft = record.stage_id and record.stage_id.name == 'Draft'

    @api.depends('stage_id', 'stage_id.name')
    def _compute_is_waiting_approval(self):
        """Compute if estimation is waiting for approval"""
        for record in self:
            record.is_waiting_approval = record.stage_id and record.stage_id.name == 'Waiting Approval'

    @api.depends('stage_id', 'stage_id.name')
    def _compute_is_approved(self):
        """Compute if estimation is approved"""
        for record in self:
            record.is_approved = record.stage_id and record.stage_id.name == 'Approved'

    @api.depends('stage_id', 'stage_id.is_locked_stage')
    def _compute_is_locked(self):
        """Compute if estimation is locked"""
        for record in self:
            record.is_locked = record.stage_id and record.stage_id.is_locked_stage

    @api.depends('stage_id', 'stage_id.color')
    def _compute_stage_color(self):
        """Update stage color when stage changes"""
        for record in self:
            record.stage_color = record.stage_id.color if record.stage_id else 0

    @api.depends('stage_id')
    def _compute_stage_flags(self):
        """Compute all stage flags together"""
        self._compute_is_waiting_approval()

    @api.constrains('estimation_date', 'validity_date')
    def _check_dates(self):
        """Validate estimation dates"""
        for record in self:
            if record.estimation_date and record.validity_date:
                if record.validity_date < record.estimation_date:
                    raise ValidationError('Validity date must be after estimation date.')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update domain for AMC Contract, Project, and Lead when partner changes"""
        if self.partner_id:
            return {
                'domain': {
                    'lead_id': [
                        ('partner_id', '=', self.partner_id.id)
                    ],
                    'amc_contract_id': [
                        ('customer_id', '=', self.partner_id.id),
                        ('active', '=', True),
                        ('stage_id.name', 'not in', ['Draft', 'Cancelled', 'Blocked'])
                    ],
                    'project_id': [
                        ('partner_id', '=', self.partner_id.id)
                    ]
                }
            }

    @api.model_create_multi
    def create(self, vals_list):
        """Set default stage if not provided"""
        for vals in vals_list:
            if 'stage_id' not in vals:
                vals['stage_id'] = self._get_default_stage()
        return super(FMAMCEstimation, self).create(vals_list)

    def write(self, vals):
        """Generate estimation number when stage changes to approved and prevent edits when locked"""
        # Check if trying to edit locked estimation
        if self and any(self.mapped('is_locked')) and not self.env.user.has_group('base.group_system'):
            if any(key in vals for key in ['line_ids', 'partner_id', 'amc_contract_id', 'project_id', 
                                          'estimation_date', 'amount_total', 'note'] if key != 'stage_id'):
                raise UserError('Cannot modify a locked estimation. Please unlock it first or contact system administrator.')
        
        result = super(FMAMCEstimation, self).write(vals)
        
        if 'stage_id' in vals:
            for estimation in self:
                if not estimation.name:
                    stage = self.env['fm.amc.estimation.stage'].browse(vals['stage_id'])
                    if stage.is_approved_stage:
                        estimation.name = estimation._generate_estimation_number()
        
        return result

    def _generate_estimation_number(self):
        """Generate estimation number based on configuration"""
        config = self.env['fm.amc.estimation.config'].get_config()
        
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
        
        # Get year from estimation date
        year = None
        if config.use_year:
            if self.estimation_date:
                year = self.estimation_date.year
            else:
                year = date.today().year
        
        # Use appropriate format based on AMC contract link
        # Check if AMC contract is actually linked (not empty)
        has_amc_contract = self.amc_contract_id and self.amc_contract_id.id
        
        if has_amc_contract and config.amc_estimation_format_text:
            # Use AMC estimation format - has AMC contract linked
            # Format: {prefix}/AMC/{modulecode}/{branchcode}/{nextnumber}/{year}
            return config.generate_estimation_number(branch_code=branch_code, year=year, use_amc_format=True)
        else:
            # Use standard format - no AMC contract linked
            # Format: {prefix}/{modulecode}/{branchcode}/{nextnumber}/{year}
            return config.generate_estimation_number(branch_code=branch_code, year=year, use_amc_format=False)

    def action_submit_for_approval(self):
        """Submit estimation for approval"""
        waiting_stage = self.env['fm.amc.estimation.stage'].search([
            ('name', '=', 'Waiting Approval'),
            ('is_default', '=', True)
        ], limit=1)
        
        if not waiting_stage:
            raise UserError('Waiting Approval stage not found. Please check stage configuration.')
        
        if not self.line_ids:
            raise UserError('Please add at least one estimation line before submitting for approval.')
        
        self.write({'stage_id': waiting_stage.id})
        self.message_post(body='Estimation submitted for approval.')
        return True

    def action_approve(self):
        """Approve estimation and generate estimation number"""
        approved_stage = self.env['fm.amc.estimation.stage'].search([
            ('name', '=', 'Approved'),
            ('is_default', '=', True)
        ], limit=1)
        
        if not approved_stage:
            raise UserError('Approved stage not found. Please check stage configuration.')
        
        for estimation in self:
            # Generate estimation number if not already generated
            if not estimation.name:
                estimation.name = estimation._generate_estimation_number()
                estimation.message_post(
                    body=f'Estimation approved. Estimation number generated: <strong>{estimation.name}</strong>'
                )
            else:
                estimation.message_post(body='Estimation approved.')
            
            # Update stage to Approved
            estimation.write({'stage_id': approved_stage.id})
        
        return True

    def action_lock(self):
        """Lock estimation"""
        locked_stage = self.env['fm.amc.estimation.stage'].search([
            ('name', '=', 'Locked'),
            ('is_default', '=', True)
        ], limit=1)
        
        if not locked_stage:
            raise UserError('Locked stage not found. Please check stage configuration.')
        
        self.write({'stage_id': locked_stage.id})
        self.message_post(body='Estimation locked.')
        return True

    def action_reset_to_draft(self):
        """Reset estimation to draft"""
        draft_stage = self.env['fm.amc.estimation.stage'].search([
            ('name', '=', 'Draft'),
            ('is_default', '=', True)
        ], limit=1)
        
        if not draft_stage:
            raise UserError('Draft stage not found. Please check stage configuration.')
        
        self.write({'stage_id': draft_stage.id})
        self.message_post(body='Estimation reset to draft.')
        return True

    def action_create_quotation(self):
        """Create a standard CRM quotation (sale.order) from approved estimation"""
        if not self.is_approved:
            raise UserError('Only approved estimations can be converted to quotations.')
        
        if self.sale_order_id:
            raise UserError('A quotation has already been created from this estimation.')
        
        if not self.line_ids:
            raise UserError('Please add at least one estimation line before creating a quotation.')
        
        # Create sale order
        sale_order_vals = {
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'origin': self.name or 'Estimation',
            'note': self.note or '',
            'project_id': self.project_id.id if self.project_id else False,
            'estimation_id': self.id,
            'is_estimation_order': True,  # Automatically check the Estimation checkbox
            'estimated_hours': self.estimated_hours or 0.0,  # Copy estimated hours
            'company_id': self.branch_id.id if self.branch_id else False,  # Copy branch/company
        }
        
        # Add contact if available
        if self.contact_id:
            sale_order_vals['partner_invoice_id'] = self.contact_id.id
        
        sale_order = self.env['sale.order'].create(sale_order_vals)
        
        # Create sale order lines from estimation lines (skip section, note, and travel lines)
        for line in self.line_ids.filtered(lambda l: not l.display_type and l.line_type != 'travel'):
            self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'product_id': line.product_id.id if line.product_id else False,
                'name': line.name,
                'product_uom_qty': line.product_uom_qty,
                'product_uom_id': line.product_uom.id if line.product_uom else False,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_id.ids)],
            })
        
        # Link estimation to created quotation
        self.write({'sale_order_id': sale_order.id})
        
        # Post message
        self.message_post(
            body=f'Quotation <strong>{sale_order.name}</strong> created from this estimation.'
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_quotation(self):
        """View the quotation created from this estimation"""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError('No quotation has been created from this estimation yet.')
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

