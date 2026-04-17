# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class FMAMCEstimationLine(models.Model):
    _name = 'fm.amc.estimation.line'
    _description = 'FM AMC Estimation Line'
    _order = 'sequence, id'

    estimation_id = fields.Many2one('fm.amc.estimation', string='Estimation', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Display Type (for section and note lines)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], string='Display Type', default=False, help='Technical field for UX purpose.')
    
    # Line Type
    line_type = fields.Selection([
        ('project', 'Project Estimation'),
        ('consumable', 'Consumable Estimation'),
        ('expense', 'Expense'),
        ('travel', 'Travel & Accommodation'),
    ], string='Line Type', required=True)
    
    # Product Information
    product_id = fields.Many2one('product.product', string='Product', help='Product for this line')
    product_template_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', store=True)
    
    # Description
    name = fields.Text(string='Description', required=True, help='Description of the estimation line')
    
    # Quantity and Pricing
    product_uom_qty = fields.Float(string='Quantity', default=1.0, digits='Product Unit of Measure')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', help='Unit of Measure')
    price_unit = fields.Float(string='Unit Price', digits='Product Price', default=0.0)
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_price_subtotal', store=True, currency_field='currency_id')
    
    # Currency
    currency_id = fields.Many2one('res.currency', string='Currency', related='estimation_id.currency_id', store=True, readonly=True)
    
    # Taxes
    tax_id = fields.Many2many('account.tax', string='Taxes', help='Taxes for this line')
    price_tax = fields.Monetary(string='Tax Amount', compute='_compute_price_subtotal', store=True, currency_field='currency_id')
    price_total = fields.Monetary(string='Total', compute='_compute_price_subtotal', store=True, currency_field='currency_id')

    @api.depends('product_uom_qty', 'price_unit', 'tax_id', 'display_type')
    def _compute_price_subtotal(self):
        """Compute subtotal with taxes"""
        for line in self:
            # Section and note lines have no price
            if line.display_type in ('line_section', 'line_note'):
                line.price_subtotal = 0.0
                line.price_tax = 0.0
                line.price_total = 0.0
            else:
                # Base subtotal
                line.price_subtotal = line.product_uom_qty * line.price_unit
                
                # Calculate taxes
                taxes = line.tax_id.compute_all(
                    line.price_unit,
                    currency=line.currency_id,
                    quantity=line.product_uom_qty,
                    product=line.product_id,
                    partner=line.estimation_id.partner_id
                )
                
                line.price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                line.price_total = line.price_subtotal + line.price_tax

    @api.model
    def default_get(self, fields_list):
        """Set default line_type and display_type from context - always enforce context"""
        res = super(FMAMCEstimationLine, self).default_get(fields_list)
        # Always prioritize context over any existing value
        if self.env.context.get('default_line_type'):
            res['line_type'] = self.env.context.get('default_line_type')
        elif 'line_type' not in res:
            # Only use fallback if no context and not in result
            res['line_type'] = 'project'
        
        # Handle display_type from context
        if self.env.context.get('default_display_type'):
            res['display_type'] = self.env.context.get('default_display_type')
            # For section and note lines, set defaults
            if res['display_type'] in ('line_section', 'line_note'):
                res['product_uom_qty'] = 0.0
                res['price_unit'] = 0.0
                if res['display_type'] == 'line_section' and 'name' not in res:
                    res['name'] = 'Section'
                elif res['display_type'] == 'line_note' and 'name' not in res:
                    res['name'] = 'Note'
        
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Set line_type and display_type from context - enforce context always"""
        # Get context values once
        context_line_type = self.env.context.get('default_line_type')
        context_display_type = self.env.context.get('default_display_type')
        
        for vals in vals_list:
            # Always prioritize context - override any existing line_type value
            if context_line_type:
                vals['line_type'] = context_line_type
            elif 'line_type' not in vals:
                # Fallback only if absolutely no context and not provided
                vals['line_type'] = 'project'
            
            # Handle display_type from context
            if context_display_type:
                vals['display_type'] = context_display_type
                # For section and note lines, ensure defaults
                if vals['display_type'] in ('line_section', 'line_note'):
                    vals['product_uom_qty'] = 0.0
                    vals['price_unit'] = 0.0
                    if 'product_id' in vals:
                        del vals['product_id']
                    if 'tax_id' in vals:
                        del vals['tax_id']
                    if vals['display_type'] == 'line_section' and not vals.get('name'):
                        vals['name'] = 'Section'
                    elif vals['display_type'] == 'line_note' and not vals.get('name'):
                        vals['name'] = 'Note'
        
        result = super(FMAMCEstimationLine, self).create(vals_list)
        return result

    def write(self, vals):
        """Prevent changing line_type after creation"""
        if 'line_type' in vals:
            for line in self:
                if line.line_type and line.line_type != vals['line_type']:
                    raise UserError(f'Cannot change line type from {line.line_type} to {vals["line_type"]}. Each line must stay in its designated tab.')
        return super(FMAMCEstimationLine, self).write(vals)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Update line when product changes"""
        if self.product_id and not self.display_type:
            if not self.name:
                self.name = self.product_id.name
            if not self.product_uom:
                self.product_uom = self.product_id.uom_id
            if not self.price_unit:
                self.price_unit = self.product_id.list_price
            # Set default taxes
            if self.product_id.taxes_id:
                self.tax_id = [(6, 0, self.product_id.taxes_id.ids)]
    
    @api.constrains('display_type', 'product_id', 'product_uom_qty', 'price_unit')
    def _check_section_note_lines(self):
        """Ensure section and note lines don't have product, quantity, or price"""
        for line in self:
            if line.display_type in ('line_section', 'line_note'):
                if line.product_id:
                    raise UserError('Section and note lines cannot have a product.')
                if line.product_uom_qty != 0:
                    raise UserError('Section and note lines cannot have quantity.')
                if line.price_unit != 0:
                    raise UserError('Section and note lines cannot have a price.')



