# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ChequeBook(models.Model):
    _name = 'cheque.book'
    _description = "Bank Cheque Book"
    _check_company_auto = True

    name = fields.Char(string="Name", required=True)
    bank_id = fields.Many2one('bank.cheque', string="Bank Cheque", required=True, check_company=True)
    account_number = fields.Char(string="Account Number", required=True)
    total_leaves = fields.Integer(string="Total Leaves", required=True)
    cheque_background = fields.Binary("Cheque Background Image", attachment=True)
    bank_cheque = fields.Char("Bank Cheque")
    pay_to = fields.Char("Pay To")
    cheque_from = fields.Integer(string="Cheque Number From")
    cheque_to = fields.Integer(string="Cheque Number To", compute="_compute_cheque_to", store=True)

    cheque_date = fields.Date("Date")

    is_from_date_readonly = fields.Boolean("From Date Readonly")
    is_to_date_readonly = fields.Boolean("To Date Readonly")

    cheque_leaf_ids = fields.One2many('cheque.leaf', 'cheque_book_id', string="Cheque Leaves")

    issued_cheques = fields.Integer(string="Issued Cheques", compute="_compute_issued_cheques", store=True)
    is_total_leaves_read_only = fields.Boolean("Read only leaves")
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, ondelete='cascade')
    company_ids = fields.Many2many('res.company', 'cheque_book_company_rel', 'cheque_book_id', 'company_id', string='Allowed Companies', help="Companies that can access this cheque book")

    @api.constrains('account_number')
    def _check_account_number_numeric(self):
        """Validate account number contains only digits"""
        for record in self:
            if record.account_number and not record.account_number.isdigit():
                raise ValidationError("Account number must contain only digits.")

    @api.constrains('cheque_from')
    def _check_cheque_from_required(self):
        """Ensure cheque_from is filled"""
        for record in self:
            if not record.cheque_from:
                raise ValidationError("Please fill in the 'Cheque Number From' field before saving.")

    @api.depends('cheque_from', 'total_leaves')
    def _compute_cheque_to(self):
        """Auto-sets the cheque_to field based on total_leaves"""
        for record in self:
            if record.cheque_from and record.total_leaves:
                record.cheque_to = record.cheque_from + record.total_leaves - 1
            else:
                record.cheque_to = 0

    @api.model_create_multi
    def create(self, vals_list):
        """Automatically create cheque leaves when a cheque book is created"""
        cheque_books = super(ChequeBook, self).create(vals_list)
        for cheque_book in cheque_books:
            cheque_book.write({
                'is_total_leaves_read_only': True,
                'is_from_date_readonly': True,
                'is_to_date_readonly': True
            })
            if cheque_book.cheque_from and cheque_book.total_leaves:
                cheque_leaves = []
                for number in range(cheque_book.cheque_from, cheque_book.cheque_to + 1):
                    cheque_leaves.append({
                        'name': f'Cheque {number}',
                        'number': str(number),
                        'cheque_book_id': cheque_book.id,
                    })
                cheque_book.cheque_leaf_ids = [(0, 0, leaf) for leaf in cheque_leaves]

        return cheque_books

    @api.depends('cheque_leaf_ids.is_used')
    def _compute_issued_cheques(self):
        """Compute the number of issued cheques"""
        for record in self:
            record.issued_cheques = len(record.cheque_leaf_ids.filtered(lambda c: c.is_used))


class ChequeLeaf(models.Model):
    _name = 'cheque.leaf'
    _description = "Bank Cheque Leaf"
    _rec_name = 'display_name'
    _check_company_auto = True

    name = fields.Char(string="Name", required=True)
    number = fields.Char(string="Cheque Number", required=True)
    payee_name = fields.Char(string="Payee Name")
    amount = fields.Float(string="Amount")
    date = fields.Date(string="Date")
    is_used = fields.Boolean(string="Used", default=False)
    is_cancelled = fields.Boolean(string="Cancelled", default=False)
    remark = fields.Text(string="Remark", help="Additional notes or remarks for this cheque")
    pay_to = fields.Char("Pay To")

    cheque_book_id = fields.Many2one('cheque.book', string="Cheque Book", ondelete='cascade', required=True, check_company=True)
    company_id = fields.Many2one('res.company', string='Company', related='cheque_book_id.company_id', store=True, readonly=True)
    
    display_name = fields.Char(string="Display Name", compute="_compute_display_name", store=True)

    @api.depends('number', 'cheque_book_id.name')
    def _compute_display_name(self):
        """Compute display name as {number} ({cheque_book_name})"""
        for record in self:
            if record.number and record.cheque_book_id:
                record.display_name = "%s (%s)" % (record.number, record.cheque_book_id.name)
            elif record.number:
                record.display_name = record.number
            else:
                record.display_name = record.name or 'New'

