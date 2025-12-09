# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCQuotationServiceType(models.Model):
    _name = 'amc.quotation.service.type'
    _description = 'AMC Quotation Service Type'
    _rec_name = 'system_type_id'
    _order = 'sequence, id'

    quotation_id = fields.Many2one('amc.quotation', string='Quotation', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    system_type_id = fields.Many2one('fm.amc.system.type', string='Service Type', required=True, index=True, help='Select service type')
    name = fields.Char(string='Name', related='system_type_id.name', store=True, readonly=True)
    number = fields.Integer(string='Number', related='system_type_id.number', store=True, readonly=True)
    times = fields.Selection([
        ('times_in_year', 'Times in Year'),
        ('times_in_month', 'Times in Month'),
        ('times_in_week', 'Times in Week'),
    ], string='Times', related='system_type_id.times', store=True, readonly=True)
    
    @api.onchange('system_type_id')
    def _onchange_system_type_id(self):
        """Update parent quotation's products and scope when service type is selected"""
        if not self.quotation_id:
            return
        
        # Collect all devices from all selected services
        products_data = {}
        scope_parts = []
        
        for service_line in self.quotation_id.service_type_ids:
            service = service_line.system_type_id
            if not service:
                continue
            
            # Collect scope of work description
            if service.description:
                scope_parts.append(service.description)
            
            # Collect devices/products
            for device in service.device_ids:
                if device.product_id:
                    product_key = device.product_id.id
                    if product_key not in products_data:
                        products_data[product_key] = {
                            'product_id': device.product_id.id,
                            'quantity': 0.0,
                            'uom_id': device.product_id.uom_id.id if device.product_id.uom_id else False,
                        }
                    # Sum quantities if same product appears in multiple services
                    products_data[product_key]['quantity'] += device.quantity
        
        # Clear existing product lines first (5, 0, 0 means unlink all)
        product_lines = [(5, 0, 0)]
        
        # Then add aggregated product lines
        for product_data in products_data.values():
            product_lines.append((0, 0, product_data))
        
        # Combine scope of work descriptions
        combined_scope = ''
        if scope_parts:
            # Combine HTML descriptions with separator
            combined_scope = '<hr/>'.join(scope_parts)
        
        # Update parent quotation's products and scope
        self.quotation_id.product_ids = product_lines
        self.quotation_id.scope_of_work = combined_scope
