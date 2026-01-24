# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AMCQuotation(models.Model):
    _name = 'amc.quotation'
    _description = 'AMC Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'

    # ==================== Customer & Project Info ====================
    name = fields.Char(string='Quotation Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True, domain="[('is_company', '=', True)]")
    contact_id = fields.Many2one('res.partner', string='Contact', tracking=True, domain="[('parent_id', '=', customer_id), ('is_company', '=', False)]")
    project_id = fields.Many2one('project.project', string='Project', tracking=True, help='Project from fm_amc_estimation')
    site_id = fields.Char(string='Project Site', tracking=True, help='Project site location')
    quotation_date = fields.Date(string='Quotation Date', default=fields.Date.context_today, required=True, tracking=True)
    with_stamp = fields.Boolean(string='With Stamp', default=False, help='Check if stamp is required')
    invoice_without_header = fields.Boolean(string='Invoice Without Header', default=False, help='Check if invoice should be without header')
    
    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)
    
    # ==================== Quotation Details Section ====================
    subject = fields.Char(string='Subject', help='Subject of the quotation')
    validity_id = fields.Many2one('fm.amc.contract.period', string='Validity', help='Validity period - select from Contract Periods')
    payment_terms_id = fields.Many2one('account.payment.term', string='Payment Terms', help='Payment terms - auto-filled from AMC Settings')
    number_of_schedules = fields.Integer(string='No: Of Schedules', default=0, help='Number of schedules')
    call_outs_included = fields.Integer(string='Callouts', default=0, help='Number of callouts included')
    amount = fields.Monetary(string='Amount', currency_field='currency_id', default=0.0, help='Total amount')
    exclusions = fields.Html(string='Exclusions', help='Exclusions in payment terms')
    
    # Commercial Part (Single HTML text box)
    commercial_part = fields.Html(string='Commercial Part', help='Commercial part description with rich text formatting')
    
    # ==================== Terms & Conditions Tab ====================
    terms_condition_id = fields.Many2one('fm.amc.terms.condition', string='Terms & Conditions', help='Select terms and conditions from AMC Settings')
    terms_condition_description = fields.Html(string='Description', help='Terms and conditions description - auto-loaded from selection')
    
    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """Clear contact when customer changes"""
        if self.customer_id:
            # Reset contact when customer changes
            self.contact_id = False
        else:
            self.contact_id = False
    
    @api.onchange('terms_condition_id')
    def _onchange_terms_condition_id(self):
        """Auto-load description when terms and condition is selected"""
        if self.terms_condition_id and self.terms_condition_id.description:
            self.terms_condition_description = self.terms_condition_id.description
        elif not self.terms_condition_id:
            self.terms_condition_description = False
    
    @api.onchange('service_type_ids')
    def _onchange_service_type_ids(self):
        """Auto-generate products and scope of work when service types change"""
        # Collect all devices from selected services
        products_data = {}
        scope_parts = []
        
        for service_line in self.service_type_ids:
            service = service_line.system_type_id
            if not service:
                continue
            
            # Collect scope of work description
            if service.description:
                scope_parts.append(service.description)
            
            # Collect devices/products
            for device in service.device_ids:
                if device.product_id:
                    product_key = device.product_id.id
                    if product_key not in products_data:
                        products_data[product_key] = {
                            'product_id': device.product_id.id,
                            'quantity': 0.0,
                            'uom_id': device.product_id.uom_id.id if device.product_id.uom_id else False,
                        }
                    # Sum quantities if same product appears in multiple services
                    products_data[product_key]['quantity'] += device.quantity
        
        # Clear existing product lines first (5, 0, 0 means unlink all)
        product_lines = [(5, 0, 0)]
        
        # Then add aggregated product lines
        for product_data in products_data.values():
            product_lines.append((0, 0, product_data))
        
        # Combine scope of work descriptions
        combined_scope = ''
        if scope_parts:
            # Combine HTML descriptions with separator
            combined_scope = '<hr/>'.join(scope_parts)
        
        # Update products and scope of work
        self.product_ids = product_lines
        self.scope_of_work = combined_scope
    
    # ==================== Types of Service Tab ====================
    # Service Types (One2many - can add lines)
    service_type_ids = fields.One2many('amc.quotation.service.type', 'quotation_id', string='Service Types', help='Service types for this quotation')
    
    # Buildings (One2many)
    building_ids = fields.One2many('amc.quotation.building', 'quotation_id', string='Buildings', help='Buildings and locations')
    
    # Products (One2many - populated by Generate button)
    product_ids = fields.One2many('amc.quotation.product', 'quotation_id', string='Products', help='Products required - generated from selected services')
    
    # Scope of Work (Html - combines descriptions from selected services)
    scope_of_work = fields.Html(string='Scope of Work', help='Scope of work description - combined from selected services')
    
    # ==================== Financial Fields ====================
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id, required=True)
    
    # ==================== Computed Fields ====================
    # Amount is now manual entry, not computed from lines
    
    # ==================== Auto-fill Logic ====================
    @api.model
    def default_get(self, fields_list):
        """Auto-fill validity and payment terms from AMC Settings"""
        res = super(AMCQuotation, self).default_get(fields_list)
        
        # Auto-fill validity from default contract period
        default_period = self.env['fm.amc.contract.period'].search([('active', '=', True)], order='number_of_days', limit=1)
        if default_period and 'validity_id' in fields_list:
            res['validity_id'] = default_period.id
        
        # Auto-fill payment terms from AMC Contract Config (if available)
        # Note: Payment terms are typically in account.payment.term, 
        # but we can set a default if configured in AMC settings
        # For now, we'll leave it empty and let user select
        
        return res
    
    @api.model
    def create(self, vals):
        """Generate quotation reference"""
        if vals.get('name', _('New')) == _('New') or not vals.get('name'):
            # Generate quotation number
            vals['name'] = self.env['ir.sequence'].next_by_code('amc.quotation') or _('New')
        return super(AMCQuotation, self).create(vals)
    
    def action_confirm(self):
        """Confirm quotation"""
        self.write({'status': 'confirmed'})
        return True
    
    def action_draft(self):
        """Set quotation to draft"""
        self.write({'status': 'draft'})
        return True
    
