# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractEstimation(models.Model):
    """Extend amc.contract to show linked Estimations and Sale Orders in tabs."""
    _inherit = 'amc.contract'

    # ── Estimations linked to this contract ──────────────────────────────────
    estimation_ids = fields.One2many(
        'fm.amc.estimation',
        'amc_contract_id',
        string='Estimations',
        readonly=True,
    )
    estimation_count = fields.Integer(
        string='Estimation Count',
        compute='_compute_estimation_count',
        store=True,
    )

    # ── Sale Orders created from estimations linked to this contract ──────────
    contract_sale_order_ids = fields.Many2many(
        'sale.order',
        string='Sale Orders',
        compute='_compute_contract_sale_orders',
        store=False,
    )
    contract_sale_order_count = fields.Integer(
        string='Sale Order Count',
        compute='_compute_contract_sale_orders',
    )

    @api.depends('estimation_ids')
    def _compute_estimation_count(self):
        for contract in self:
            contract.estimation_count = len(contract.estimation_ids)

    @api.depends('estimation_ids.sale_order_id')
    def _compute_contract_sale_orders(self):
        for contract in self:
            # Sale orders created via Estimations linked to this contract
            from_estimations = contract.estimation_ids.mapped('sale_order_id').filtered(bool)
            # Sale orders directly linked to this contract via amc_contract_id field
            direct_orders = self.env['sale.order'].search([
                ('amc_contract_id', '=', contract.id)
            ])
            all_orders = from_estimations | direct_orders
            contract.contract_sale_order_ids = all_orders
            contract.contract_sale_order_count = len(all_orders)

    # ── Invoices linked to this contract ──────────────────────────────────────
    contract_invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices',
        compute='_compute_contract_invoices',
        store=False,
    )
    contract_invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_contract_invoices',
    )

    @api.depends('contract_sale_order_ids.invoice_ids')
    def _compute_contract_invoices(self):
        for contract in self:
            # Invoices generated from the sale orders linked to this contract
            sale_invoices = contract.contract_sale_order_ids.mapped('invoice_ids').filtered(
                lambda inv: inv.move_type in ('out_invoice', 'out_refund', 'out_receipt')
            )
            # Invoices directly linked to this contract via amc_contract_id field
            direct_invoices = self.env['account.move'].search([
                ('amc_contract_id', '=', contract.id),
                ('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt'))
            ])
            all_invoices = sale_invoices | direct_invoices
            contract.contract_invoice_ids = all_invoices
            contract.contract_invoice_count = len(all_invoices)
