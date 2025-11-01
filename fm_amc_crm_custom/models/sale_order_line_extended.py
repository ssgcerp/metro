# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    estimated_price = fields.Monetary(string='Estimated Price', compute='_compute_estimated_price',
                                     store=False, currency_field='currency_id',
                                     help='Estimated price from the linked estimation')

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

