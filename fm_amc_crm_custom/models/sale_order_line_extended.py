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
        # If we're loading from estimation, preserve the existing name
        if self.env.context.get('from_estimation_load') or self._preserve_name_on_change:
            old_name = self.name if self.name else None
            # Try to call parent method if it exists
            try:
                res = super().product_id_change()
            except AttributeError:
                # Base method doesn't exist or was renamed in Odoo 19
                res = {}
            # Restore the estimation description
            if old_name:
                self.name = old_name
            return res
        # Normal behavior - call parent if it exists
        try:
            return super().product_id_change()
        except AttributeError:
            # Base method doesn't exist in Odoo 19, return empty dict
            return {}

