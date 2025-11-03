# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
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
    
    @api.model_create_multi
    def create(self, vals_list):
        """Inherit product type from category if not specified"""
        for vals in vals_list:
            # If type is not specified and category has a product_type, use it
            if 'type' not in vals or not vals.get('type'):
                categ_id = vals.get('categ_id')
                if categ_id:
                    category = self.env['product.category'].browse(categ_id)
                    if category.product_type:
                        vals['type'] = category.product_type
        return super().create(vals_list)
    
    @api.onchange('type')
    def _onchange_type_filter_category(self):
        """Filter categories based on selected product type and clear category if it doesn't match"""
        if self.type:
            # If current category doesn't match the type, clear it
            if self.categ_id and self.categ_id.product_type and self.categ_id.product_type != self.type:
                self.categ_id = False
        return {
            'domain': {
                'categ_id': self._get_category_domain()
            }
        }
    
    @api.onchange('categ_id')
    def _onchange_categ_id_product_type(self):
        """Auto-set product type from category when category changes"""
        if self.categ_id and self.categ_id.product_type and not self.type:
            self.type = self.categ_id.product_type
            return {
                'domain': {
                    'categ_id': self._get_category_domain()
                }
            }
    
    def _get_category_domain(self):
        """Get domain for category field based on product type"""
        if self.type:
            # Show categories that match the product type OR categories without product_type set (for flexibility)
            return ['|', ('product_type', '=', self.type), ('product_type', '=', False)]
        else:
            # If no type selected, show all categories (no restriction)
            return []
    


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
            'view_mode': 'list,form',
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

