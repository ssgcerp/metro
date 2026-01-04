from odoo import models, fields, api


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    bank_reference = fields.Char(string='Bank Reference', copy=False)
    cheque_reference = fields.Char(string='Cheque Reference', copy=False)
    effective_date = fields.Date(string='Effective Date', help='Effective date of PDC', copy=False, default=False)
    check_number = fields.Char(string='Check Number', copy=False)
    payment_method_code = fields.Char(string='Payment Method Code', compute='_compute_payment_method_code', store=False)
    cheque_leaf_id = fields.Many2one(
        'cheque.leaf',
        string='Cheque Number',
        domain="[('is_used', '=', False), ('is_cancelled', '=', False)]",
        check_company=True,
        help='Select an available cheque number from the cheque book',
        copy=False,
    )

    @api.depends('payment_method_line_id')
    def _compute_payment_method_code(self):
        """Compute payment method code for visibility conditions"""
        for record in self:
            record.payment_method_code = record.payment_method_line_id.code if record.payment_method_line_id else False

    @api.onchange('payment_method_line_id', 'journal_id')
    def _onchange_payment_method_or_journal(self):
        """Update domain for cheque_leaf_id when payment method or journal changes"""
        domain = []
        if self.journal_id and self.journal_id.company_id:
            domain.append(('company_id', '=', self.journal_id.company_id.id))
        domain.extend([
            ('is_used', '=', False),
            ('is_cancelled', '=', False)
        ])
        return {
            'domain': {
                'cheque_leaf_id': domain
            }
        }

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
        # Domain update is handled by _onchange_payment_method_or_journal
        return self._onchange_payment_method_or_journal()

    def _create_payment_vals_from_batch(self, batch_result):
        """Override to include PDC fields in payment creation"""
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_batch(batch_result)
        payment_vals.update({
            'bank_reference': self.bank_reference,
            'cheque_reference': self.cheque_reference,
            'effective_date': self.effective_date,
            'check_number': self.check_number,
            'cheque_leaf_id': self.cheque_leaf_id.id if self.cheque_leaf_id else False,
        })
        return payment_vals

