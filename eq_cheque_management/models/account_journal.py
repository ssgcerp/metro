# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    allow_cheque = fields.Boolean(
        string='Allow Cheque',
        default=False,
        help='Enable cheque payment methods for this journal',
    )

    # =========================== Built-in functions =========================== #
    @api.model
    def _get_reusable_payment_methods(self):
        """Add PDC and CDC payment method codes to reusable payment methods"""
        res = super(AccountJournal, self)._get_reusable_payment_methods()
        res.add("pdc")
        res.add("cdc")
        return res

