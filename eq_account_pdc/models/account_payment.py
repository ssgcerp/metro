from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    bank_reference = fields.Char(copy=False)
    cheque_reference = fields.Char(copy=False)
    effective_date = fields.Date(string='Effective Date', help='Effective date of PDC', copy=False, default=False)
    cheque_leaf_id = fields.Many2one(
        'cheque.leaf',
        string='Cheque Number',
        domain="[('is_used', '=', False), ('is_cancelled', '=', False)]",
        check_company=True,
        help='Select an available cheque number from the cheque book',
        copy=False,
    )

    # =========================== Compute functions =========================== #
    @api.depends('payment_method_line_id.code', 'check_number')
    def _compute_show_check_number(self):
        for payment in self:
            payment.show_check_number = (
                    payment.payment_method_line_id.code in ['check_printing', 'pdc']
                    and payment.check_number
            )

    @api.onchange('cheque_leaf_id')
    def _onchange_cheque_leaf_id(self):
        """Auto-fill check_number when cheque leaf is selected"""
        if self.cheque_leaf_id:
            self.check_number = self.cheque_leaf_id.number

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Reset cheque leaf when journal changes to ensure company match"""
        if self.journal_id and self.cheque_leaf_id:
            if self.cheque_leaf_id.company_id != self.journal_id.company_id:
                self.cheque_leaf_id = False
                self.check_number = False
        return {
            'domain': {
                'cheque_leaf_id': [
                    ('company_id', '=', self.journal_id.company_id.id if self.journal_id else False),
                    ('is_used', '=', False),
                    ('is_cancelled', '=', False)
                ]
            }
        }

    # =========================== Built-in functions =========================== #
    def print_checks(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        # Since this method can be called via a client_action_multi, we need to make sure the received records are what we expect
        self = self.filtered(lambda r: r.payment_method_line_id.code in ['check_printing', 'pdc'] and r.state != 'reconciled')

        if len(self) == 0:
            raise UserError(_("Payments to print as a checks must have 'Check' selected as payment method and "
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

    @api.model
    def create(self, values):
        payment = super(AccountPayment, self).create(values)
        if payment.memo:
            for line in payment.move_id.line_ids.filtered(
                    lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')):
                line.name = payment.memo
        # Mark cheque leaf as used if selected
        if payment.cheque_leaf_id and payment.state in ('posted', 'sent', 'reconciled'):
            payment.cheque_leaf_id.write({'is_used': True})
        return payment

    def write(self, values):
        """Mark cheque leaf as used when payment is posted"""
        result = super(AccountPayment, self).write(values)
        if 'state' in values and values['state'] in ('posted', 'sent', 'reconciled'):
            for payment in self:
                if payment.cheque_leaf_id and not payment.cheque_leaf_id.is_used:
                    payment.cheque_leaf_id.write({'is_used': True})
        return result

