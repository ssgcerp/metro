# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    brand_variant_id = fields.Many2one(
        'product.brand.variant',
        string='Brand Variant',
        help='Brand variant for this stock move',
        index=True
    )
    
    @api.onchange('product_id', 'brand_variant_id')
    def _onchange_product_brand_variant(self):
        """Update move when brand variant changes"""
        if self.brand_variant_id and self.brand_variant_id.list_price:
            self.price_unit = self.brand_variant_id.list_price

