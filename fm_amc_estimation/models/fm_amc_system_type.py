# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FMAMCSystemType(models.Model):
    _name = 'fm.amc.system.type'
    _description = 'AMC System Type'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Name', required=True, help='Name of the system type (e.g., FIRE EXTINGUISHERS)')
    number = fields.Integer(string='Number', default=1, help='Number value for the system type')
    times = fields.Selection([
        ('times_in_year', 'Times in Year'),
        ('times_in_month', 'Times in Month'),
        ('times_in_week', 'Times in Week'),
    ], string='Times', default='times_in_year', required=True, help='Frequency of maintenance')
    description = fields.Html(string='Description', help='Description of the system type with rich text formatting')
    active = fields.Boolean(string='Active', default=True, help='If unchecked, it will allow you to hide the system type without removing it.')
    
    # Devices Required (One-to-Many)
    device_ids = fields.One2many('fm.amc.system.type.device', 'system_type_id', string='Devices Required', help='Products/devices required for this system type')


class FMAMCSystemTypeDevice(models.Model):
    _name = 'fm.amc.system.type.device'
    _description = 'AMC System Type Device'
    _rec_name = 'product_id'
    _order = 'id'

    system_type_id = fields.Many2one('fm.amc.system.type', string='System Type', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, help='Product/device required for this system type')
    quantity = fields.Float(string='Quantity', default=0.0, digits='Product Unit of Measure', help='Required quantity of the product')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, help='Unit of Measure of the product')
