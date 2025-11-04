# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    estimated_price = fields.Monetary(string='Estimated Price', compute='_compute_estimated_price',
                                     store=False, currency_field='currency_id',
                                     help='Estimated price from the linked estimation')
    
    _preserve_name_on_change = fields.Boolean(default=False, help='Flag to preserve name when product_id changes')

    @api.depends('product_id', 'order_id.estimation_id')
    def _compute_estimated_price(self):
        """Compute estimated price from estimation lines"""
        for line in self:
            if line.order_id.estimation_id and line.product_id:
                # Search for product in estimation lines
                estimation = line.order_id.estimation_id
                estimated_line = None
                
                # Search in line_ids
                for est_line in estimation.line_ids:
                    if est_line.product_id.id == line.product_id.id:
                        estimated_line = est_line
                        break
                
                line.estimated_price = estimated_line.unit_price if estimated_line else 0.0
            else:
                line.estimated_price = 0.0
    
    @api.onchange('product_id')
    def product_id_change(self):
        """Override to preserve description when loading from estimation"""
        # Check if we should preserve the name (from estimation load)
        preserve_name = self.env.context.get('from_estimation_load') or self._preserve_name_on_change
        
        # Store the old name if we need to preserve it
        old_name = self.name if preserve_name and self.name else None
        
        # Try to get parent method safely using getattr
        parent_method = getattr(super(), 'product_id_change', None)
        
        # Call parent method if it exists, otherwise return empty dict
        if parent_method:
            res = parent_method()
        else:
            # Base method doesn't exist in Odoo 19, return empty dict
            res = {}
        
        # Restore the estimation description if we were preserving it
        if preserve_name and old_name:
            self.name = old_name
        
        return res

