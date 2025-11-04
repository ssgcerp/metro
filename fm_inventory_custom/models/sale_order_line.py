# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    brand_variant_id = fields.Many2one(
        'product.brand.variant',
        string='Brand Variant',
        domain="[('product_template_id', '=', product_id.product_tmpl_id)]",
        help='Select brand variant for this line'
    )
    
    @api.onchange('product_id')
    def _onchange_product_id_brand(self):
        """Update brand variant when product changes"""
        if self.product_id:
            # Clear brand variant if product changed
            if self.brand_variant_id:
                if self.brand_variant_id.product_template_id != self.product_id.product_tmpl_id:
                    self.brand_variant_id = False
    
    @api.onchange('brand_variant_id')
    def _onchange_brand_variant_id(self):
        """Update price and description when brand variant changes"""
        if self.brand_variant_id:
            if self.brand_variant_id.list_price:
                self.price_unit = self.brand_variant_id.list_price
            
            # Update description to include brand
            if self.product_id:
                brand_name = self.brand_variant_id.brand_id.name
                if brand_name and brand_name not in (self.name or ''):
                    if self.name:
                        self.name = f"[{brand_name}] {self.name}"
                    else:
                        self.name = f"[{brand_name}] {self.product_id.name}"
    
    def _prepare_procurement_values(self, group_id=False):
        """Add brand variant to procurement values"""
        values = super()._prepare_procurement_values(group_id)
        if self.brand_variant_id:
            values['brand_variant_id'] = self.brand_variant_id.id
        return values

