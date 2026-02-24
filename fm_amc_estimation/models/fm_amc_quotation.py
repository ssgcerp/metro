# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FMAMCQuotation(models.Model):
    _name = 'fm.amc.quotation'
    _description = 'AMC Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'

    def _default_stage(self):
        """Get default stage from quotation stages"""
        return self.env['fm.amc.quotation.stage'].search([('is_default', '=', True)], order='sequence', limit=1) or self.env['fm.amc.quotation.stage'].search([], limit=1)

    # Basic Information
    name = fields.Char(string='Quotation Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    project_site = fields.Char(string='Project Site', tracking=True)
    contact_id = fields.Many2one('res.partner', string='Contact', domain="[('parent_id', '=', partner_id)]", tracking=True)
    user_id = fields.Many2one('res.users', string='Sales Contact', default=lambda self: self.env.user, tracking=True)
    
    # Quotation Details
    date_quotation = fields.Date(string='Quotation Date', default=fields.Date.context_today, required=True, tracking=True)
    with_stamp = fields.Boolean(string='With Stamp', default=False)
    branch_id = fields.Many2one('res.company', string='Branch', tracking=True, default=lambda self: self.env.company)
    branch = fields.Char(string='Branch', compute='_compute_branch', store=True, readonly=True)
    
    @api.depends('branch_id')
    def _compute_branch(self):
        """Compute branch name"""
        for record in self:
            record.branch = record.branch_id.name if record.branch_id else ''
    invoice_without_header = fields.Boolean(string='Invoice Without Header', default=False)
    
    # Stage
    stage_id = fields.Many2one('fm.amc.quotation.stage', string='Stage', default=_default_stage, ondelete='set null', tracking=True, help='Quotation stage')
    
    # Quotation Details Tab
    subject = fields.Text(string='Subject', help='Subject of the quotation')
    validity_id = fields.Many2one('fm.amc.contract.period', string='Validity', help='Contract validity period')
    payment_terms_id = fields.Many2one('account.payment.term', string='Payment Terms', help='Payment terms for the quotation')
    exclusions = fields.Html(string='Payment Terms Exclusions', help='Exclusions in payment terms')
    no_of_schedules = fields.Integer(string='No: Of Schedules', default=0, help='Number of schedules')
    callouts_amount = fields.Monetary(string='Callouts Amount', currency_field='currency_id', default=0.0, help='Callouts amount')
    commercial_part = fields.Html(string='Commercial Part', help='Commercial part description')
    amount = fields.Monetary(string='Amount', currency_field='currency_id', compute='_compute_amount', store=True, help='Total amount')
    
    # Terms and Condition Tab
    terms_condition_id = fields.Many2one('fm.amc.terms.condition', string='Terms and Condition', help='Predefined terms and condition')
    terms_condition_description = fields.Html(string='Terms and Condition', help='Terms and condition description')
    
    @api.onchange('terms_condition_id')
    def _onchange_terms_condition_id(self):
        """Load terms and condition description when selected"""
        if self.terms_condition_id and self.terms_condition_id.description:
            self.terms_condition_description = self.terms_condition_id.description
    
    # Types of Services Tab
    system_type_ids = fields.One2many('fm.amc.quotation.system.type', 'quotation_id', string='System Types', help='System types for this quotation')
    building_ids = fields.One2many('fm.amc.quotation.building', 'quotation_id', string='Buildings', help='Buildings and locations')
    product_ids = fields.One2many('fm.amc.quotation.product', 'quotation_id', string='Products', help='Products required')
    scope_of_work = fields.Html(string='Scope of Work', help='Scope of work description')
    
    # Financial
    amount_total = fields.Monetary(string='Total Amount', currency_field='currency_id', compute='_compute_amount_total', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id, required=True)
    
    # Other
    active = fields.Boolean(default=True)
    revision_count = fields.Integer(string='Revision Count', default=0, readonly=True)
    
    @api.depends('callouts_amount', 'building_ids.unit_price', 'product_ids.price_subtotal')
    def _compute_amount(self):
        """Compute total amount from callouts, buildings, and products"""
        for record in self:
            building_total = sum(record.building_ids.mapped('unit_price'))
            product_total = sum(record.product_ids.mapped('price_subtotal'))
            record.amount = record.callouts_amount + building_total + product_total
    
    @api.depends('amount')
    def _compute_amount_total(self):
        """Compute total amount"""
        for record in self:
            record.amount_total = record.amount
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate quotation reference"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New') or not vals.get('name'):
                # Generate quotation number similar to estimation
                vals['name'] = self.env['ir.sequence'].next_by_code('fm.amc.quotation') or _('New')
        return super(FMAMCQuotation, self).create(vals_list)
    
    def action_create_contract(self):
        """Create contract from quotation"""
        # This will be implemented to create AMC contract
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Contract',
            'res_model': 'amc.contract',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_quotation_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }
    
    def action_create_revision(self):
        """Create revision of quotation"""
        self.ensure_one()
        revision = self.copy({
            'revision_count': self.revision_count + 1,
            'name': f"{self.name}-R{self.revision_count + 1}",
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation Revision',
            'res_model': 'fm.amc.quotation',
            'res_id': revision.id,
            'view_mode': 'form',
            'target': 'current',
        }


class FMAMCQuotationSystemType(models.Model):
    _name = 'fm.amc.quotation.system.type'
    _description = 'AMC Quotation System Type'
    _rec_name = 'system_type_id'
    _order = 'sequence, id'

    quotation_id = fields.Many2one('fm.amc.quotation', string='Quotation', required=True, ondelete='cascade', index=True)
    system_type_id = fields.Many2one('fm.amc.system.type', string='System Type', required=True, index=True)
    name = fields.Char(string='Name', related='system_type_id.name', store=True, readonly=True)
    number = fields.Integer(string='Number', related='system_type_id.number', store=True, readonly=True)
    times = fields.Selection([
        ('times_in_year', 'Times in Year'),
        ('times_in_month', 'Times in Month'),
        ('times_in_week', 'Times in Week'),
    ], string='Times', related='system_type_id.times', store=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)


class FMAMCQuotationBuilding(models.Model):
    _name = 'fm.amc.quotation.building'
    _description = 'AMC Quotation Building'
    _rec_name = 'building_name'
    _order = 'sequence, id'

    quotation_id = fields.Many2one('fm.amc.quotation', string='Quotation', required=True, ondelete='cascade', index=True)
    building_name = fields.Char(string='Building Name', required=True)
    location = fields.Char(string='Location')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency', related='quotation_id.currency_id', store=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)


class FMAMCQuotationProduct(models.Model):
    _name = 'fm.amc.quotation.product'
    _description = 'AMC Quotation Product'
    _rec_name = 'product_id'
    _order = 'sequence, id'

    quotation_id = fields.Many2one('fm.amc.quotation', string='Quotation', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    quantity = fields.Float(string='Quantity', default=1.0, digits='Product Unit of Measure')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True)
    price_unit = fields.Monetary(string='Unit Price', currency_field='currency_id', default=0.0)
    price_subtotal = fields.Monetary(string='Subtotal', currency_field='currency_id', compute='_compute_price_subtotal', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='quotation_id.currency_id', store=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        """Compute subtotal"""
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Update fields when product changes"""
        if self.product_id:
            if not self.price_unit:
                self.price_unit = self.product_id.list_price
