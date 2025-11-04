# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'
    _order = 'name'

    name = fields.Char(string='Brand Name', required=True, translate=True)
    code = fields.Char(string='Brand Code', help='Short code for the brand')
    logo = fields.Image(string='Brand Logo', max_width=1024, max_height=1024)
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(string='Active', default=True)
    
    # Statistics
    product_count = fields.Integer(string='Products', compute='_compute_product_count')
    product_variant_count = fields.Integer(string='Product Variants', compute='_compute_product_count')
    
    @api.depends('product_template_ids', 'product_template_ids.product_variant_ids')
    def _compute_product_count(self):
        for brand in self:
            templates = brand.product_template_ids
            brand.product_count = len(templates)
            brand.product_variant_count = len(templates.mapped('product_variant_ids'))
    
    # Relationships
    product_template_ids = fields.One2many(
        'product.template',
        'brand_id',
        string='Products',
        help='Products associated with this brand'
    )
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Brand name must be unique!'),
    ]

