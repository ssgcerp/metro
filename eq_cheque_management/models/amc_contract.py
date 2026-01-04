# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContract(models.Model):
    _inherit = 'amc.contract'

    # PDC Cheque Integration
    incoming_cheque_ids = fields.One2many(
        'eq.cheque.incoming',
        'contract_id',
        string='Incoming PDC Cheques',
    )
    outgoing_cheque_ids = fields.One2many(
        'eq.cheque.outgoing',
        'contract_id',
        string='Outgoing PDC Cheques',
    )
    
    # Computed Fields for PDC Tracking
    total_incoming_pdc_amount = fields.Monetary(
        string='Total Incoming PDC Amount',
        compute='_compute_pdc_amounts',
        store=True,
        currency_field='currency_id',
    )
    pending_incoming_pdc_amount = fields.Monetary(
        string='Pending Incoming PDC Amount',
        compute='_compute_pdc_amounts',
        store=True,
        currency_field='currency_id',
    )
    cleared_incoming_pdc_amount = fields.Monetary(
        string='Cleared Incoming PDC Amount',
        compute='_compute_pdc_amounts',
        store=True,
        currency_field='currency_id',
    )
    bounced_incoming_pdc_amount = fields.Monetary(
        string='Bounced Incoming PDC Amount',
        compute='_compute_pdc_amounts',
        store=True,
        currency_field='currency_id',
    )
    
    total_outgoing_pdc_amount = fields.Monetary(
        string='Total Outgoing PDC Amount',
        compute='_compute_pdc_amounts',
        store=True,
        currency_field='currency_id',
    )
    pending_outgoing_pdc_amount = fields.Monetary(
        string='Pending Outgoing PDC Amount',
        compute='_compute_pdc_amounts',
        store=True,
        currency_field='currency_id',
    )
    cleared_outgoing_pdc_amount = fields.Monetary(
        string='Cleared Outgoing PDC Amount',
        compute='_compute_pdc_amounts',
        store=True,
        currency_field='currency_id',
    )
    bounced_outgoing_pdc_amount = fields.Monetary(
        string='Bounced Outgoing PDC Amount',
        compute='_compute_pdc_amounts',
        store=True,
        currency_field='currency_id',
    )
    
    incoming_cheque_count = fields.Integer(
        string='Incoming Cheques Count',
        compute='_compute_cheque_counts',
    )
    outgoing_cheque_count = fields.Integer(
        string='Outgoing Cheques Count',
        compute='_compute_cheque_counts',
    )

    @api.depends('incoming_cheque_ids', 'incoming_cheque_ids.amount', 'incoming_cheque_ids.state',
                 'outgoing_cheque_ids', 'outgoing_cheque_ids.amount', 'outgoing_cheque_ids.state')
    def _compute_pdc_amounts(self):
        """Compute PDC amounts for contract"""
        for record in self:
            # Incoming cheques
            incoming_cheques = record.incoming_cheque_ids.filtered(lambda c: c.cheque_type == 'pdc')
            record.total_incoming_pdc_amount = sum(incoming_cheques.mapped('amount'))
            record.pending_incoming_pdc_amount = sum(
                incoming_cheques.filtered(lambda c: c.state in ('draft', 'registered')).mapped('amount')
            )
            record.cleared_incoming_pdc_amount = sum(
                incoming_cheques.filtered(lambda c: c.state in ('deposited', 'done')).mapped('amount')
            )
            record.bounced_incoming_pdc_amount = sum(
                incoming_cheques.filtered(lambda c: c.state == 'bounced').mapped('amount')
            )
            
            # Outgoing cheques
            outgoing_cheques = record.outgoing_cheque_ids.filtered(lambda c: c.cheque_type == 'pdc')
            record.total_outgoing_pdc_amount = sum(outgoing_cheques.mapped('amount'))
            record.pending_outgoing_pdc_amount = sum(
                outgoing_cheques.filtered(lambda c: c.state in ('draft', 'registered')).mapped('amount')
            )
            record.cleared_outgoing_pdc_amount = sum(
                outgoing_cheques.filtered(lambda c: c.state in ('deposited', 'done')).mapped('amount')
            )
            record.bounced_outgoing_pdc_amount = sum(
                outgoing_cheques.filtered(lambda c: c.state == 'bounced').mapped('amount')
            )

    @api.depends('incoming_cheque_ids', 'outgoing_cheque_ids')
    def _compute_cheque_counts(self):
        """Compute cheque counts"""
        for record in self:
            record.incoming_cheque_count = len(record.incoming_cheque_ids)
            record.outgoing_cheque_count = len(record.outgoing_cheque_ids)

    def action_view_incoming_cheques(self):
        """Open incoming cheques for this contract"""
        self.ensure_one()
        action = {
            'name': 'Incoming PDC Cheques',
            'type': 'ir.actions.act_window',
            'res_model': 'eq.cheque.incoming',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }
        return action

    def action_view_outgoing_cheques(self):
        """Open outgoing cheques for this contract"""
        self.ensure_one()
        action = {
            'name': 'Outgoing PDC Cheques',
            'type': 'ir.actions.act_window',
            'res_model': 'eq.cheque.outgoing',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }
        return action

