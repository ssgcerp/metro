# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProjectEstimationSalesLine(models.Model):
    _name = 'project.estimation.sales.line'
    _description = 'Project Estimation Sales Line'
    _order = 'sequence, id'
    
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Product Information
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        help='Product for this estimation line'
    )
    product_reference = fields.Char(
        string='Product Reference',
        related='product_id.default_code',
        store=True,
        readonly=True,
        help='Product reference code'
    )
    
    # Brand Information
    brand_id = fields.Many2one(
        'product.brand',
        string='Brand',
        related='product_id.brand_id',
        store=True,
        readonly=True,
        help='Product brand'
    )
    
    # Description
    description = fields.Text(
        string='Description',
        required=True,
        help='Description of the estimation line'
    )
    
    # Quantity and Unit
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
        digits='Product Unit of Measure'
    )
    product_uom = fields.Many2one(
        'uom.uom',
        string='Unit',
        related='product_id.uom_id',
        store=True,
        readonly=True,
        help='Unit of Measure'
    )
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Update line when product changes"""
        if self.product_id:
            if not self.description:
                self.description = self.product_id.name
            if not self.product_uom:
                self.product_uom = self.product_id.uom_id


class ProjectConsumableLine(models.Model):
    _name = 'project.consumable.line'
    _description = 'Project Consumable Line'
    _order = 'sequence, id'
    
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity', default=1.0, digits='Product Unit of Measure')
    product_uom = fields.Many2one('uom.uom', string='Unit', related='product_id.uom_id', store=True, readonly=True)


class ProjectDeliveryIndent(models.Model):
    _name = 'project.delivery.indent'
    _description = 'Project Delivery Indent'
    _order = 'date desc, id'
    
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    name = fields.Char(string='Indent Number', required=True, default='New')
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    partner_id = fields.Many2one('res.partner', string='Vendor/Customer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    notes = fields.Text(string='Notes')


class ProjectInventoryReturn(models.Model):
    _name = 'project.inventory.return'
    _description = 'Project Inventory Return'
    _order = 'date desc, id'
    
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    name = fields.Char(string='Return Number', required=True, default='New')
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    partner_id = fields.Many2one('res.partner', string='Return To')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    notes = fields.Text(string='Notes')


class ProjectChequeDetail(models.Model):
    _name = 'project.cheque.detail'
    _description = 'Project Cheque Detail'
    _order = 'cheque_date desc, id'
    
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    cheque_number = fields.Char(string='Cheque Number', required=True)
    cheque_date = fields.Date(string='Cheque Date', required=True)
    bank_name = fields.Char(string='Bank Name')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    partner_id = fields.Many2one('res.partner', string='Payee/Payer')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('cleared', 'Cleared'),
        ('bounced', 'Bounced'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    notes = fields.Text(string='Notes')

