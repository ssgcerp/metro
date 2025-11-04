# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    # Product Type field for category
    # This allows setting a default product type at category level
    product_type = fields.Selection(
        [
            ('product', 'Goods'),
            ('consu', 'Consumable'),
            ('service', 'Service'),
        ],
        string='Product Type',
        help='Default product type for products in this category. If set, new products in this category will automatically use this type.'
    )

