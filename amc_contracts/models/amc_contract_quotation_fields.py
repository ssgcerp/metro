# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AMCContractEstimationLine(models.Model):
    _name = 'amc.contract.estimation.line'
    _description = 'AMC Estimation Line'

    contract_id = fields.Many2one('amc.contract', string="AMC Contract", ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Description')
    product_qty = fields.Float(string='Quantity', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    
    unit_cost = fields.Float(string='Unit Cost')
    service_cost = fields.Float(string='Service Cost')
    net_cost = fields.Float(string='Net Cost')
    profit = fields.Float(string='Profit')
    profit_percent = fields.Float(string='Profit Percent')
    
    service_subtotal = fields.Float(string='Service Subtotal')
    unit_selling_price = fields.Float(string='Unit Selling Price')
    selling_price = fields.Float(string='Selling Price')
    
    unit_total = fields.Float(string='Unit Total Price')
    total_selling_service = fields.Float(string='Total Selling With Service')


class AMCContractQuotationFields(models.Model):
    _inherit = 'amc.contract'

    # Extracted Quotation String/Text Fields
    heading = fields.Char(string='Quotation Heading')
    scope = fields.Text(string='Scope of Work')
    exclusions = fields.Text(string='Exclusions')
    terms_and_condition = fields.Text(string='Terms and Conditions')
    commercial_part_data = fields.Text(string='Commercial Part Data')
    
    lpo_number = fields.Char(string='LPO Number')
    lpo_date = fields.Date(string='LPO Date')
    
    revision_number = fields.Char(string='Revision Number')
    validity_text = fields.Char(string='Validity')
    
    quotation_date = fields.Date(string='Quotation Date')
    
    # Estimation Lines
    estimation_product_ids = fields.One2many('amc.contract.estimation.line', 'contract_id', string="Estimation Lines")
    
    # Computed Totals (Stored for migration)
    quotation_service_cost = fields.Float(string='Service Cost Total')
    quotation_expense_total = fields.Float(string='Expense Total')
    quotation_amc_total = fields.Float(string='AMC Total')
    quotation_total_value = fields.Float(string='Total Quotation Value')
