# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import float_is_zero, float_compare
from itertools import groupby
from ast import literal_eval


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('discount_type', 'discount_rate', 'amount_untaxed')
    def _compute_amount_all(self):
        for order in self:
            order.amount_grand = order.amount_untaxed
            if (order.discount_type == 'percent'):
                order.amount_discount = round((order.amount_grand * order.discount_rate / 100), 2)
            elif (order.discount_type == 'amount'):
                order.amount_discount = order.discount_rate
            else:
                order.amount_discount = 0.0
            order.amount_total_with_discount = order.amount_grand - order.amount_discount

    type = fields.Selection([('discount', 'Discount'), ('retention', 'Retention')], 'Type', readonly=True)
    discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')], 'Discount Type', readonly=True)
    discount_rate = fields.Float('Discount Rate', readonly=True)
    discount_narration = fields.Char('Discount Narration', readonly=True)
    retention_rate = fields.Float('Retention Rate', readonly=True)
    analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    amount_discount = fields.Float(string='Discount', digits=(16, 2),
                                   store=True, readonly=True, compute='_compute_amount_all', tracking=True)
    amount_grand = fields.Float(string='Total', digits=(16, 2),
                                store=True, readonly=True, compute='_compute_amount_all', tracking=True)
    amount_total_with_discount = fields.Float('Total', readonly=True, compute='_compute_amount_all')
    is_tax_after_discount = fields.Boolean(string='Tax After Discount', readonly=True)

    def apply_retention(self):
        print('111111111111', self)
        print('2222222222', self.discount_rate)
        if self.retention_rate > 0:
            print('3333333333333')
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
            print('444444444444', default_retention_product)
            if self.amount_tax:
                mapped_taxes = self.order_line.mapped('tax_id')
                tax_id = mapped_taxes[0] if mapped_taxes else False
                self.order_line = [(0, 0, {'product_id': default_retention_product,
                                           'product_uom_qty': -1,
                                           'price_unit': self.retention_rate,
                                           'tax_id': [(6, 0, [tax_id.id])] if tax_id else False})]
            else:
                self.order_line = [(0, 0, {'product_id': default_retention_product,
                                           'product_uom_qty': -1,
                                           'price_unit': self.retention_rate,
                                           'tax_id': False
                                           })]
            print('555555555555')

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.amount_discount > 0:
            res.update({
                'type': self.type or '',
                'discount_type': self.discount_type or '',
                'discount_rate': self.discount_rate or '',
                'is_tax_after_discount': self.is_tax_after_discount,
                'discount_narration': self.discount_narration or '',
                'retention_rate': self.retention_rate or '',
                'analytic_id': self.analytic_id.id or '',
                'amount_grand': self.amount_grand,
                'amount_discount': self.amount_discount,
            })
        else:
            res.update({
                'type': self.type or '',
                'discount_type': self.discount_type or '',
                'discount_rate': self.discount_rate or '',
                'is_tax_after_discount': self.is_tax_after_discount,
                'discount_narration': self.discount_narration or '',
                'retention_rate': self.retention_rate or '',
                'analytic_id': self.analytic_id.id or '',
                'amount_grand': self.amount_grand,
                'amount_discount': self.amount_discount,
            })

        return res

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0  # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            current_section_vals = None
            down_payments = order.env['sale.order.line']

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    invoice_line_vals.append(
                        (0, 0, order._prepare_down_payment_section_line(
                            sequence=invoice_item_sequence,
                        )),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line(
                        sequence=invoice_item_sequence,
                    )),
                )
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise self._nothing_to_invoice_error()

        # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(invoice_vals_list,
                                       key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys])
            for grouping_keys, invoices in groupby(invoice_vals_list,
                                                   key=lambda x: [x.get(grouping_key) for grouping_key in
                                                                  invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence,
                                                                                   old=line[2]['sequence'])
                    sequence += 1

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)
        moves.apply_discount()
        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_invoice_into_refund_credit_note()
        for move in moves:
            move.message_post_with_view('mail.message_origin_link',
                                        values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
                                        subtype_id=self.env.ref('mail.mt_note').id
                                        )
        return moves

