# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Estimation SKU field - will be shown in Estimations and Quotations
    estimation_sku = fields.Char(string='Estimation SKU', 
                                  help='Estimation SKU for estimations and quotations')
    
    # Default SKU field - will be shown in Sales Orders
    default_sku = fields.Char(string='Default SKU', 
                              help='Default SKU for sales orders')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate SKUs if not provided"""
        for vals in vals_list:
            # Generate estimation SKU if not provided
            if 'estimation_sku' not in vals or not vals.get('estimation_sku'):
                config = self.env['fm.amc.product.sku.config'].get_config()
                vals['estimation_sku'] = config.generate_estimation_sku()
            
            # Generate default SKU if not provided
            if 'default_sku' not in vals or not vals.get('default_sku'):
                config = self.env['fm.amc.product.sku.config'].get_config()
                vals['default_sku'] = config.generate_default_sku()
        
        return super(ProductTemplate, self).create(vals_list)

