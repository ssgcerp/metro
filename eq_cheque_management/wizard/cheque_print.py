# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ChequePrint(models.TransientModel):
    _name = 'cheque.print'
    _description = "Cheque Print Wizard"

    pay_to = fields.Char("Pay To", required=True)
    cheque_date = fields.Date("Cheque Date", default=fields.Date.today)
    amount = fields.Monetary("Amount", currency_field='currency_id', required=True)
    amount_in_words = fields.Char("Amount in Words Line 1")
    amount_in_words_2 = fields.Char("Amount in Words Line 2")
    amt_2_words = fields.Char("Amount in Words (Full)")
    account_number = fields.Char(related="cheque_book_id.account_number", string="Account Number", readonly=True)
    print_a_c_label = fields.Boolean(string="A/C Pay Label", default=False)
    move_id = fields.Many2one('account.move')
    report_preview = fields.Html()
    show_preview = fields.Boolean('Show Preview?')

    # MANY2ONE FIELDS
    cheque_book_id = fields.Many2one("cheque.book", 'Cheque Book', required=True)
    cheque_background = fields.Binary("Cheque Background Image")
    cheque_number_id = fields.Many2one(
        "cheque.leaf",
        string="Cheque Number",
        domain="[('cheque_book_id', '=', cheque_book_id),('is_used', '=', False)]"
    )

    customer_id = fields.Many2one("res.partner", 'Customer')
    date_on_cheque = fields.Date("Date on cheque", default=fields.Date.today)

    # CURRENCY FIELDS
    print_currency = fields.Boolean(string="Print Currency", default=True)
    currency_id = fields.Many2one('res.currency', string="Currency", required=True, default=lambda self: self.env.company.currency_id)
    currency_symbol = fields.Char(related="currency_id.symbol", string="Currency Symbol", readonly=True)

    # DYNAMIC FIELD POSITIONS FOR DRAG & DROP
    pay_to_x = fields.Integer(string="Payee X", default=100)
    pay_to_y = fields.Integer(string="Payee Y", default=50)

    amount_x = fields.Integer(string="Amount X", default=500)
    amount_y = fields.Integer(string="Amount Y", default=200)

    date_x = fields.Integer(string="Date X", default=600)
    date_y = fields.Integer(string="Date Y", default=50)

    @api.onchange('amount', 'currency_id', 'print_currency')
    def _onchange_amount_in_words(self):
        """Compute amount in words when amount or currency changes"""
        for record in self:
            if record.amount and record.currency_id:
                full_text = record.currency_id.amount_to_text(record.amount).replace(",", "").title()
                
                if record.print_currency:
                    full_text = f"{full_text} Only"

                record.amt_2_words = full_text

                # Split the sentence into two lines
                words = full_text.split()
                first_line = ""
                second_line = ""
                for word in words:
                    if len(first_line) + len(word) + 1 <= 65:
                        if first_line:
                            first_line += " "
                        first_line += word
                    else:
                        if second_line:
                            second_line += " "
                        second_line += word

                record.amount_in_words = first_line
                record.amount_in_words_2 = second_line
            else:
                record.amount_in_words = ""
                record.amount_in_words_2 = ""
                record.amt_2_words = ""

    @api.onchange('cheque_book_id')
    def _onchange_cheque_book(self):
        """Update cheque background when cheque book changes"""
        for record in self:
            if record.cheque_book_id and record.cheque_book_id.bank_id:
                record.cheque_background = record.cheque_book_id.bank_id.cheque_image
            else:
                record.cheque_background = False

    @api.onchange('cheque_number_id')
    def _check_cheque_issue(self):
        """Validate that cheque number is not already used"""
        for record in self:
            if record.cheque_number_id and record.cheque_number_id.is_used:
                raise ValidationError(
                    f"The cheque number '{record.cheque_number_id.number}' has already been used. Please select another cheque."
                )

    def action_print_preview(self):
        """Show preview of the cheque"""
        for record in self:
            record.show_preview = True
            record.cheque_background = record.cheque_book_id.bank_id.cheque_image or False

            if record.amount and record.currency_id:
                amount_words = record.currency_id.amount_to_text(record.amount).replace(",", "").title()
                if record.print_currency:
                    amount_words = f"{amount_words} Only"

                record.amt_2_words = amount_words

                words = amount_words.split()
                line1 = ""
                line2 = ""
                max_line1_length = 65

                for word in words:
                    if len(line1 + ' ' + word) <= max_line1_length:
                        if line1:
                            line1 += ' ' + word
                        else:
                            line1 = word
                    else:
                        remaining_words = words[words.index(word):]
                        line2 = ' '.join(remaining_words)
                        break

                record.amount_in_words = line1
                record.amount_in_words_2 = line2

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_hide_preview(self):
        """Hide preview"""
        self.show_preview = False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_print_cheque(self):
        """Print the cheque and mark it as used"""
        for record in self:
            record.cheque_background = record.cheque_book_id.bank_id.cheque_image or False

            if record.amount and record.currency_id:
                amount_words = record.currency_id.amount_to_text(record.amount).replace(",", "").title()
                if record.print_currency:
                    amount_words = f"{amount_words} Only"

                record.amt_2_words = amount_words

                words = amount_words.split()
                first_line = ""
                second_line = ""
                for word in words:
                    if len(first_line) + len(word) + 1 <= 65:
                        if first_line:
                            first_line += " "
                        first_line += word
                    else:
                        if second_line:
                            second_line += " "
                        second_line += word

                record.amount_in_words = first_line
                record.amount_in_words_2 = second_line

            # Enforce usage check and mark cheque as used
            if record.cheque_number_id:
                if record.cheque_number_id.is_used:
                    raise ValidationError(
                        f"The cheque number '{record.cheque_number_id.number}' has already been used. Please select another cheque."
                    )
                record.cheque_number_id.is_used = True
                record.cheque_number_id.amount = record.amount
                record.cheque_number_id.payee_name = record.pay_to
                record.cheque_number_id.date = record.cheque_date or record.date_on_cheque
                record.cheque_number_id.pay_to = record.pay_to

        return self.env.ref('eq_cheque_management.action_cheque_print_report').report_action(self)

