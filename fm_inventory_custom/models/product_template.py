# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # New product types
    product_type_custom = fields.Selection(
        selection=[
            ('consumable_custom', 'Consumable'),
            ('storable_custom', 'Storable Product'),
        ],
        string='Product Type (Custom)',
        help='Custom product type classification',
        default='storable_custom'
    )
    
    # Brand relationship (primary brand)
    brand_id = fields.Many2one(
        'product.brand',
        string='Brand',
        help='Primary brand for this product'
    )
    
    # Brand variants (One2many to product.brand.variant)
    brand_variant_ids = fields.One2many(
        'product.brand.variant',
        'product_template_id',
        string='Brand Variants',
        help='Multiple brand variants with individual pricing and stock tracking'
    )
    
    @api.model
    def _get_product_type_default(self):
        """Get default product type"""
        return 'storable_custom'
    
    @api.onchange('product_type_custom')
    def _onchange_product_type_custom(self):
        """Map custom types to standard Odoo types"""
        type_mapping = {
            'consumable_custom': 'consu',
            'storable_custom': 'product',
        }
        if self.product_type_custom in type_mapping:
            self.type = type_mapping[self.product_type_custom]
    
    @api.model_create_multi
    def create(self, vals_list):
        """Set default type if not provided"""
        for vals in vals_list:
            if 'type' not in vals and 'product_type_custom' not in vals:
                vals['product_type_custom'] = 'storable_custom'
                vals['type'] = 'product'
            elif 'product_type_custom' in vals and 'type' not in vals:
                type_mapping = {
                    'consumable_custom': 'consu',
                    'storable_custom': 'product',
                }
                if vals['product_type_custom'] in type_mapping:
                    vals['type'] = type_mapping[vals['product_type_custom']]
        return super().create(vals_list)


class ProductBrandVariant(models.Model):
    """Brand variants for products with brand-specific pricing and stock"""
    _name = 'product.brand.variant'
    _description = 'Product Brand Variant'
    _order = 'brand_id, sequence'
    
    name = fields.Char(string='Variant Name', compute='_compute_name', store=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    product_template_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        ondelete='cascade'
    )
    
    brand_id = fields.Many2one(
        'product.brand',
        string='Brand',
        required=True,
        ondelete='restrict'
    )
    
    # Brand-specific pricing
    list_price = fields.Float(
        string='Sales Price',
        digits='Product Price',
        help='Brand-specific sales price'
    )
    
    # Brand-specific stock tracking
    stock_qty = fields.Float(
        string='Available Quantity',
        compute='_compute_stock_qty',
        help='Brand-specific available quantity across all locations'
    )
    
    # Location-wise stock
    location_stock_ids = fields.One2many(
        'product.brand.stock',
        'brand_variant_id',
        string='Location Stock',
        help='Stock levels per warehouse location'
    )
    
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
        ('product_brand_uniq', 'unique(product_template_id, brand_id)', 
         'Each product can only have one variant per brand!'),
    ]
    
    @api.depends('product_template_id', 'brand_id')
    def _compute_name(self):
        for variant in self:
            if variant.product_template_id and variant.brand_id:
                variant.name = f"{variant.product_template_id.name} - {variant.brand_id.name}"
            else:
                variant.name = False
    
    @api.depends('location_stock_ids.quantity')
    def _compute_stock_qty(self):
        for variant in self:
            variant.stock_qty = sum(variant.location_stock_ids.mapped('quantity'))
    
    def action_open_stock_locations(self):
        """Open stock locations for this brand variant"""
        self.ensure_one()
        return {
            'name': f'Stock Locations - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.brand.stock',
            'view_mode': 'tree,form',
            'domain': [('brand_variant_id', '=', self.id)],
            'context': {
                'default_brand_variant_id': self.id,
            }
        }


class ProductBrandStock(models.Model):
    """Stock tracking per brand variant and location"""
    _name = 'product.brand.stock'
    _description = 'Brand Variant Stock by Location'
    _order = 'location_id, brand_variant_id'
    
    brand_variant_id = fields.Many2one(
        'product.brand.variant',
        string='Brand Variant',
        required=True,
        ondelete='cascade'
    )
    
    product_template_id = fields.Many2one(
        'product.template',
        related='brand_variant_id.product_template_id',
        string='Product',
        store=True,
        readonly=True
    )
    
    brand_id = fields.Many2one(
        'product.brand',
        related='brand_variant_id.brand_id',
        string='Brand',
        store=True,
        readonly=True
    )
    
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
        domain=[('usage', 'in', ['internal', 'transit'])],
        ondelete='restrict'
    )
    
    quantity = fields.Float(
        string='Quantity',
        default=0.0,
        digits='Product Unit of Measure'
    )
    
    reserved_quantity = fields.Float(
        string='Reserved Quantity',
        default=0.0,
        digits='Product Unit of Measure'
    )
    
    available_quantity = fields.Float(
        string='Available',
        compute='_compute_available_quantity',
        store=True
    )
    
    _sql_constraints = [
        ('brand_location_uniq', 'unique(brand_variant_id, location_id)',
         'Each brand variant can only have one stock record per location!'),
    ]
    
    @api.depends('quantity', 'reserved_quantity')
    def _compute_available_quantity(self):
        for stock in self:
            stock.available_quantity = stock.quantity - stock.reserved_quantity

