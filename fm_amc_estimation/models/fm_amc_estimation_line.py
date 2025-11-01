# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FMAMCEstimationLine(models.Model):
    _name = 'fm.amc.estimation.line'
    _description = 'FM AMC Estimation Line'
    _order = 'sequence, id'

    estimation_id = fields.Many2one('fm.amc.estimation', string='Estimation', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Line Type
    line_type = fields.Selection([
        ('project', 'Project Estimation'),
        ('consumable', 'Consumable Estimation'),
        ('expense', 'Expense'),
    ], string='Line Type', required=True, default='project')
    
    # Product Information
    product_id = fields.Many2one('product.product', string='Product', help='Product for this line')
    product_template_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', store=True)
    
    # Description
    name = fields.Text(string='Description', required=True, help='Description of the estimation line')
    
    # Quantity and Pricing
    product_uom_qty = fields.Float(string='Quantity', default=1.0, required=True, digits='Product Unit of Measure')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', help='Unit of Measure')
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price')
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_price_subtotal', store=True, currency_field='currency_id')
    
    # Currency
    currency_id = fields.Many2one('res.currency', string='Currency', related='estimation_id.currency_id', store=True, readonly=True)
    
    # Taxes
    tax_id = fields.Many2many('account.tax', string='Taxes', help='Taxes for this line')
    price_tax = fields.Monetary(string='Tax Amount', compute='_compute_price_subtotal', store=True, currency_field='currency_id')
    price_total = fields.Monetary(string='Total', compute='_compute_price_subtotal', store=True, currency_field='currency_id')

    @api.depends('product_uom_qty', 'price_unit', 'tax_id')
    def _compute_price_subtotal(self):
        """Compute subtotal with taxes"""
        for line in self:
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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Update line when product changes"""
        if self.product_id:
            if not self.name:
                self.name = self.product_id.name
            if not self.product_uom:
                self.product_uom = self.product_id.uom_id
            if not self.price_unit:
                self.price_unit = self.product_id.list_price
            # Set default taxes
            if self.product_id.taxes_id:
                self.tax_id = [(6, 0, self.product_id.taxes_id.ids)]



