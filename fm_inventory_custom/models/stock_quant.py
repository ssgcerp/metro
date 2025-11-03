# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    brand_variant_id = fields.Many2one(
        'product.brand.variant',
        string='Brand Variant',
        help='Brand variant for this stock quant',
        index=True
    )
    
    @api.model
    def _get_inventory_fields_create(self):
        """Add brand_variant_id to inventory fields"""
        res = super()._get_inventory_fields_create()
        res.append('brand_variant_id')
        return res
    
    @api.model
    def _get_inventory_fields_write(self):
        """Add brand_variant_id to inventory fields"""
        res = super()._get_inventory_fields_write()
        res.append('brand_variant_id')
        return res

