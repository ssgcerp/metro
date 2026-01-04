# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    bank_reference = fields.Char(string='Bank Reference', copy=False, help='Bank reference number')
    cheque_reference = fields.Char(string='Cheque Reference', copy=False, help='Cheque reference number')
    effective_date = fields.Date(
        string='Effective Date',
        help='Effective date of PDC (Post Dated Cheque)',
        copy=False,
        default=False,
    )

    # =========================== Compute functions =========================== #
    @api.depends('payment_method_line_id.code', 'check_number')
    def _compute_show_check_number(self):
        """Extend to include PDC payment methods"""
        res = super(AccountPayment, self)._compute_show_check_number()
        for payment in self:
            if not payment.show_check_number:
                payment.show_check_number = (
                    payment.payment_method_line_id.code in ['pdc', 'pdc_in', 'pdc_out', 'cdc', 'cdc_in', 'cdc_out']
                    and payment.check_number
                )
        return res

    # =========================== Built-in functions =========================== #
    def print_checks(self):
        """Extend print_checks to include PDC payment methods"""
        # Filter for cheque payment methods including our PDC codes
        cheque_codes = ['check_printing', 'pdc', 'pdc_in', 'pdc_out', 'cdc', 'cdc_in', 'cdc_out']
        self = self.filtered(
            lambda r: r.payment_method_line_id.code in cheque_codes and r.state != 'reconciled'
        )

        if len(self) == 0:
            raise UserError(_("Payments to print as checks must have a cheque payment method selected and "
                            "not have already been reconciled"))
        if any(payment.journal_id != self[0].journal_id for payment in self):
            raise UserError(_("In order to print multiple checks at once, they must belong to the same bank journal."))

        if not self[0].journal_id.check_manual_sequencing:
            # The wizard asks for the number printed on the first pre-printed check
            # so payments are attributed the number of the check the'll be printed on.
            self.env.cr.execute("""
                  SELECT payment.id
                    FROM account_payment payment
                    JOIN account_move move ON move.id = payment.move_id
                   WHERE journal_id = %(journal_id)s
                     AND payment.check_number IS NOT NULL
                ORDER BY payment.check_number::BIGINT DESC
                   LIMIT 1
            """, {
                'journal_id': self.journal_id.id,
            })
            last_printed_check = self.browse(self.env.cr.fetchone())
            number_len = len(last_printed_check.check_number or "")
            next_check_number = '%0{}d'.format(number_len) % (int(last_printed_check.check_number) + 1)

            return {
                'name': _('Print Pre-numbered Checks'),
                'type': 'ir.actions.act_window',
                'res_model': 'print.prenumbered.checks',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'payment_ids': self.ids,
                    'default_next_check_number': next_check_number,
                }
            }
        else:
            self.filtered(lambda r: r.state == 'draft').action_post()
            return self.do_print_checks()

