# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleQuotationConfig(models.Model):
    _name = 'sale.quotation.config'
    _description = 'Sale Quotation Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, default='Quotation Configuration')
    
    # Stage Color Configuration
    draft_stage_color = fields.Integer(string='Draft Stage Color', default=0)
    pending_approval_stage_color = fields.Integer(string='Pending Approval Stage Color', default=5)
    quotation_stage_color = fields.Integer(string='Quotation Stage Color', default=10)
    quotation_sent_stage_color = fields.Integer(string='Quotation Sent Stage Color', default=3)
    sales_order_stage_color = fields.Integer(string='Sales Order Stage Color', default=4)
    cancelled_stage_color = fields.Integer(string='Cancelled Stage Color', default=1)
    
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Configuration name must be unique!'),
    ]

    @api.model
    def get_config(self):
        """Get active configuration or create default"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({'name': 'Default Quotation Configuration'})
        return config

