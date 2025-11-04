# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    brand_id = fields.Many2one(
        'product.brand',
        related='product_tmpl_id.brand_id',
        string='Brand',
        store=True,
        readonly=True
    )
    
    brand_variant_ids = fields.One2many(
        'product.brand.variant',
        related='product_tmpl_id.brand_variant_ids',
        string='Brand Variants',
        readonly=True
    )

