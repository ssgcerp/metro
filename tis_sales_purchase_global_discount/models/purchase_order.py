# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from ast import literal_eval


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.price_total', 'order_line.price_tax', 'discount_type', 'discount_rate', 'is_tax_after_discount', 'amount_untaxed', 'amount_tax')
    def _compute_amount_all(self):
        for order in self:
            order.amount_grand = order.amount_untaxed
            order.amount_total_with_discount = order.amount_grand
            if (order.discount_type == 'percent'):
                order.amount_discount = round((order.amount_grand * order.discount_rate / 100), 2)
            elif (order.discount_type == 'amount'):
                order.amount_discount = order.discount_rate
            else:
                order.amount_discount = 0.0
            if (order.amount_grand >= order.amount_discount):
                order.amount_total_with_discount = order.amount_grand - order.amount_discount
                if order.is_tax_after_discount:
                    # Recompute tax based on discounted amount
                    order.amount_tax = round((order.amount_total_with_discount * 5) / 100, 2)
                # else: keep the original amount_tax from order lines
                # Compute the final total with discount
                order.amount_total = round((order.amount_untaxed + order.amount_tax) - order.amount_discount, 2)
            else:
                order.amount_total_with_discount = order.amount_grand
                # Keep original amount_total if discount is invalid
                if not order.amount_total:
                    order.amount_total = order.amount_untaxed + order.amount_tax

    type = fields.Selection([('discount', 'Discount'), ('retention', 'Retention')], 'Type', readonly=True)
    discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')], 'Discount Type',
                                     readonly=True)
    discount_rate = fields.Float('Discount Rate', readonly=True)
    discount_narration = fields.Char('Discount Narration', readonly=True)
    retention_rate = fields.Float('Retention Rate', readonly=True)
    analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account',
                                  readonly=True)
    amount_discount = fields.Float(string='Discount', digits=(16, 2),
                                   store=True, readonly=True, compute='_compute_amount_all', tracking=True)
    amount_grand = fields.Float(string='Total', digits=(16, 2),
                                store=True, readonly=True, compute='_compute_amount_all', tracking=True)
    amount_total = fields.Float(string='Net Total', digits=(16, 2),
                                store=True, readonly=True, compute='_compute_amount_all')
    amount_total_with_discount = fields.Float('Total', readonly=True, compute='_compute_amount_all')
    is_tax_after_discount = fields.Boolean(string='Tax After Discount', readonly=True)

    def apply_retention_amount(self):
        if self.retention_rate > 0:
            ICPSudo = self.env['ir.config_parameter'].sudo()
            retention_product_id = ICPSudo.get_param(
                'tis_sales_purchase_global_discount.retention_product_id')
            default_retention_product = False
            if not retention_product_id:
                raise UserError(
                    _('Please Configure Retention Product'))
            else:
                default_retention_product = literal_eval(
                    ICPSudo.get_param('tis_sales_purchase_global_discount.retention_product_id',
                                      default='False'))
            if self.amount_tax:
                tax_id = self.order_line.mapped('taxes_id')[0]
                self.order_line = [(0, 0, {'product_id': default_retention_product,
                                           'product_qty': -1,
                                           'price_unit': self.retention_rate,
                                           'taxes_id': [(6, 0, [tax_id.id])]})]
            else:
                self.order_line = [(0, 0, {'product_id': default_retention_product,
                                           'product_qty': -1,
                                           'price_unit': self.retention_rate,
                                           'taxes_id': False})]

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        res['type'] = self.type
        res['discount_type'] = self.discount_type
        res['is_tax_after_discount'] = self.is_tax_after_discount
        res['discount_rate'] = self.discount_rate
        res['discount_narration'] = self.discount_narration
        res['retention_rate'] = self.retention_rate
        res['analytic_id'] = self.analytic_id
        res['amount_discount'] = self.amount_discount
        if self.amount_discount > 0:
            ICPSudo = self.env['ir.config_parameter'].sudo()
            purchase_discount_account = self.env['ir.config_parameter'].sudo().get_param(
                'tis_sales_purchase_global_discount.def_discount_purchase_account_id')
            default_discount_account = False
            if not purchase_discount_account:
                raise UserError(
                    _('Please Configure  Purchase Discount Account.'))
            else:
                default_discount_account = literal_eval(
                    ICPSudo.get_param('tis_sales_purchase_global_discount.def_discount_purchase_account_id',
                                      default='False'))
            if self.amount_tax:
                tax_id = self.order_line.mapped('taxes_id')[0]
                invoice_line_ids = [(0, 0, {
                    'name': 'Discount',
                    'price_unit': -self.amount_discount,
                    'quantity': 1,
                    'move_id': self.id,
                    'currency_id': self.currency_id.id,
                    'account_id': default_discount_account,
                    'partner_id': self.partner_id.id,
                    'tax_ids': [(6, 0, [tax_id.id])] if self.is_tax_after_discount else '',
                    'exclude_from_invoice_tab': True,
                    'is_discount': True
                })]
            else:
                invoice_line_ids = [(0, 0, {
                    'name': 'Discount',
                    'price_unit': -self.amount_discount,
                    'quantity': 1,
                    'move_id': self.id,
                    'currency_id': self.currency_id.id,
                    'account_id': default_discount_account,
                    'partner_id': self.partner_id.id,
                    # 'tax_ids': [(6, 0, [19])],
                    'exclude_from_invoice_tab': True,
                    'is_discount': True
                })]

            res['invoice_line_ids'] = invoice_line_ids
        # else:
        print('ddddddddd')
        if self.retention_rate > 0:
            print('qqqqqqqqqqqqqq')
            ICPSudo = self.env['ir.config_parameter'].sudo()
            retention_product_id = ICPSudo.get_param(
                'tis_sales_purchase_global_discount.retention_product_id')
            default_retention_product = False
            if not retention_product_id:
                raise UserError(
                    _('Please Configure Retention Product'))
            else:
                default_retention_product = literal_eval(
                    ICPSudo.get_param('tis_sales_purchase_global_discount.retention_product_id',
                                      default='False'))
            print('eeeeeeeeeeeeeeeee', default_retention_product)
            if self.amount_tax:
                print('ccccccccccccccccccc', self.amount_tax)
                tax_id = self.order_line.mapped('taxes_id')[0]
                print('lllllllllll', tax_id)
                invoice_line_ids = [(0, 0, {
                    'product_id': default_retention_product,
                    'name': 'Retention',
                    'quantity': -1,
                    'price_unit': self.retention_rate,
                    'move_id': self.id,
                    'currency_id': self.currency_id.id,
                    'partner_id': self.partner_id.id,
                    'tax_ids': [(6, 0, [tax_id.id])],
                    'exclude_from_invoice_tab': False,
                })]
            else:
                print('tttttttttttttttttt')
                invoice_line_ids = [(0, 0, {
                    'product_id': default_retention_product,
                    'name': 'Retention',
                    'price_unit': self.retention_rate,
                    'quantity': -1,
                    'move_id': self.id,
                    'currency_id': self.currency_id.id,
                    'partner_id': self.partner_id.id,
                    'exclude_from_invoice_tab': False})]
            res['invoice_line_ids'] = invoice_line_ids
            print('qwerty', res['invoice_line_ids'])
        print('ffffffffffffff', res)
        return res

