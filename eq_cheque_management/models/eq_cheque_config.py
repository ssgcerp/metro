# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EqChequeConfig(models.Model):
    _name = 'eq.cheque.config'
    _description = 'Cheque Management Configuration'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
    )
    
    # PDC Account Configuration (UAE Compliant)
    pdc_receivable_account_id = fields.Many2one(
        'account.account',
        string='PDC Receivable Account',
        domain="[('account_type', '=', 'asset_current')]",
        help='Account for tracking PDC received from customers (Other Current Asset)',
    )
    pdc_payable_account_id = fields.Many2one(
        'account.account',
        string='PDC Payable Account',
        domain="[('account_type', '=', 'liability_current')]",
        help='Account for tracking PDC issued to vendors (Other Current Liability)',
    )
    pdc_clearing_account_id = fields.Many2one(
        'account.account',
        string='PDC Clearing Account',
        domain="[('account_type', '=', 'asset_current')]",
        help='Account for PDC clearing transactions (Other Current Asset)',
    )
    cheque_bounce_charges_account_id = fields.Many2one(
        'account.account',
        string='Bounce Charges Account',
        domain="[('account_type', 'in', ('income', 'expense'))]",
        help='Account for bounce charges (Income/Expense)',
    )
    
    # Default Journals
    default_incoming_journal_id = fields.Many2one(
        'account.journal',
        string='Default Incoming Journal',
        domain="[('type', '=', 'bank')]",
        help='Default bank journal for incoming cheques',
    )
    default_outgoing_journal_id = fields.Many2one(
        'account.journal',
        string='Default Outgoing Journal',
        domain="[('type', '=', 'bank')]",
        help='Default bank journal for outgoing cheques',
    )
    
    # Sequence Configuration
    incoming_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Incoming Sequence',
        help='Sequence for incoming cheque numbering (IN/YYYY/0001)',
    )
    outgoing_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Outgoing Sequence',
        help='Sequence for outgoing cheque numbering (OUT/YYYY/0001)',
    )
    
    # Settings
    allow_cancel_journal_entries = fields.Boolean(
        string='Allow Cancel Journal Entries',
        default=False,
        help='Allow cancellation of posted journal entries for returned cheques',
    )

    _sql_constraints = [
        ('company_unique', 'UNIQUE(company_id)', 'Configuration must be unique per company.'),
    ]

    @api.constrains('pdc_receivable_account_id', 'pdc_payable_account_id', 'pdc_clearing_account_id')
    def _check_accounts_configured(self):
        """Ensure PDC accounts are configured for proper accounting"""
        for record in self:
            if not record.pdc_receivable_account_id:
                raise ValidationError('PDC Receivable Account must be configured for company %s.' % record.company_id.name)
            if not record.pdc_payable_account_id:
                raise ValidationError('PDC Payable Account must be configured for company %s.' % record.company_id.name)
            if not record.pdc_clearing_account_id:
                raise ValidationError('PDC Clearing Account must be configured for company %s.' % record.company_id.name)

