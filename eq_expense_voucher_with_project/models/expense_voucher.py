from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountExpenseVoucher(models.Model):
    _name = "account.expense.voucher"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Expense Voucher"
    _order = "date desc, id desc"

    partner_id = fields.Many2one("res.partner", string="Customer")
    name = fields.Char(string="Name", readonly=True, tracking=True, default="Draft")
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="['|', ('type', '=', 'cash'), ('type', '=', 'bank')]",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    voucher_type = fields.Selection(
        [
            ("send", "Send Money"),
            ("receive", "Receive Money"),
        ],
        string="Type",
        required=True,
        default="send",
    )

    untaxed_amount = fields.Monetary(string="Untaxed Amount", compute="_compute_grand_total", currency_field="currency_id")
    tax_amount = fields.Monetary(string="Tax Amount", compute="_compute_grand_total", currency_field="currency_id")
    total_amount = fields.Monetary(string="Total", compute="_compute_grand_total", currency_field="currency_id")
    expense_line_ids = fields.One2many(
        "account.expense.voucher.line", "expense_id", string="Expense Lines"
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending Of Approval"),
            ("submit", "Approved"),
            ("posted", "Post"),
        ],
        readonly=True,
        default="draft",
        tracking=True,
    )
    payment_entry_id = fields.Many2one("account.move", string="Payment Entry", copy=False, readonly=True)
    reference = fields.Char(string="Reference")
    comments = fields.Char(string="Comments")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    is_approver = fields.Boolean(
        string="Approver",
        compute="_compute_is_expense_voucher_approver",
        default=False,
        copy=False,
    )

    @staticmethod
    def _group_user_ids(group):
        """Compatibility helper: Odoo versions may expose group users as `user_ids` or `users`."""
        if not group:
            return []
        if hasattr(group, "user_ids"):
            return group.user_ids.ids
        if hasattr(group, "users"):
            return group.users.ids
        return []

    def _compute_is_expense_voucher_approver(self):
        """Check if current user is admin or has accounting manager rights."""
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        for rec in self:
            approver_ids = set()
            if admin:
                approver_ids.add(admin.id)
            # Add users with account manager group as approvers
            account_manager_group = self.env.ref("account.group_account_manager", raise_if_not_found=False)
            if account_manager_group:
                approver_ids.update(self._group_user_ids(account_manager_group))
            rec.is_approver = self.env.user.id in approver_ids

    def _ensure_sequence(self):
        for rec in self:
            if rec.name in (False, "/", "Draft"):
                rec.name = self.env["ir.sequence"].next_by_code("expense.voucher.code") or rec.name

    def button_send_for_approval(self):
        for rec in self:
            rec._ensure_sequence()

            users = self.env["res.users"]
            admin = self.env.ref("base.user_admin", raise_if_not_found=False)
            if admin:
                users |= admin
            # Add account managers as approvers
            account_manager_group = self.env.ref("account.group_account_manager", raise_if_not_found=False)
            if account_manager_group:
                users |= self.env["res.users"].browse(self._group_user_ids(account_manager_group))

            if users:
                # Post a message on the record
                rec.message_post(
                    body=_("Expense Voucher Approval Request of %s") % rec.name,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )

                for user in users:
                    if user.partner_id.email:
                        mail = self.env["mail.mail"].create(
                            {
                                "subject": _("Expense Voucher Approval Request"),
                                "body_html": _("Expense Voucher Approval Request of (%s)") % rec.name,
                                "email_to": user.partner_id.email,
                            }
                        )
                        mail.send()

            rec.state = "pending"

    def button_reject(self):
        self.write({"state": "draft"})

    @api.depends("expense_line_ids.tax_amount", "expense_line_ids.price_amount", "expense_line_ids.subtotal")
    def _compute_grand_total(self):
        for rec in self:
            untaxed = 0.0
            tax = 0.0
            total = 0.0
            for line in rec.expense_line_ids:
                untaxed += line.price_amount
                tax += line.tax_amount
                total += line.subtotal
            rec.untaxed_amount = untaxed
            rec.tax_amount = tax
            rec.total_amount = total

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Cannot delete records in posted stage"))
        return super().unlink()

    def action_submit(self):
        self.write({"state": "submit"})

    def _get_journal_payment_account(self):
        self.ensure_one()
        return self.journal_id.default_account_id

    def _get_tax_counterpart_account(self):
        """Keep original behavior: rely on existing accounts named 'Taxes Paid/Received'."""
        self.ensure_one()
        if self.voucher_type == "send":
            acc = self.env["account.account"].search(
                [("name", "=", "Taxes Paid"), ("company_ids", "in", [self.env.company.id])], limit=1
            )
        else:
            acc = self.env["account.account"].search(
                [("name", "=", "Taxes Received"), ("company_ids", "in", [self.env.company.id])], limit=1
            )
        if not acc:
            raise UserError(
                _("Please create an account named '%s' for tax posting.")
                % ("Taxes Paid" if self.voucher_type == "send" else "Taxes Received")
            )
        return acc

    def action_post(self):
        for rec in self:
            if rec.total_amount <= 0:
                raise UserError(_("Please enter a valid amount"))
            if not rec.expense_line_ids:
                raise UserError(_("Please add expense Lines"))

            payment_account = rec._get_journal_payment_account()
            if not payment_account:
                raise UserError(_("Please configure the journal's payment accounts."))

            tax_account = rec._get_tax_counterpart_account()

            account_lines = []

            # Bank/Cash counterpart
            if rec.voucher_type == "send":
                account_lines.append(
                    [
                        0,
                        0,
                        {
                            "name": rec.name,
                            "account_id": payment_account.id,
                            "partner_id": rec.partner_id.id,
                            "debit": 0.0,
                            "credit": rec.total_amount,
                        },
                    ]
                )
            else:
                account_lines.append(
                    [
                        0,
                        0,
                        {
                            "name": rec.name,
                            "account_id": payment_account.id,
                            "partner_id": rec.partner_id.id,
                            "debit": rec.total_amount,
                            "credit": 0.0,
                        },
                    ]
                )

            total_tax = 0.0
            for line in rec.expense_line_ids:
                aml_vals = {
                    "name": line.label or rec.name,
                    "account_id": line.account_id.id,
                    "partner_id": rec.partner_id.id,
                    "tax_ids": [(6, 0, line.tax_id.ids)] if line.tax_id else False,
                    "debit": line.price_amount if rec.voucher_type == "send" else 0.0,
                    "credit": line.price_amount if rec.voucher_type == "receive" else 0.0,
                }
                # "with project": map to analytic distribution using the project's analytic account (standard Odoo)
                if line.project_id and getattr(line.project_id, "analytic_account_id", False):
                    aml_vals["analytic_distribution"] = {line.project_id.analytic_account_id.id: 100.0}

                account_lines.append([0, 0, aml_vals])
                total_tax += line.tax_amount or 0.0

            if total_tax:
                if rec.voucher_type == "send":
                    account_lines.append(
                        [
                            0,
                            0,
                            {
                                "name": rec.name,
                                "account_id": tax_account.id,
                                "partner_id": rec.partner_id.id,
                                "debit": total_tax,
                                "credit": 0.0,
                            },
                        ]
                    )
                else:
                    account_lines.append(
                        [
                            0,
                            0,
                            {
                                "name": rec.name,
                                "account_id": tax_account.id,
                                "partner_id": rec.partner_id.id,
                                "debit": 0.0,
                                "credit": total_tax,
                            },
                        ]
                    )

            move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "date": rec.date,
                    "journal_id": rec.journal_id.id,
                    "ref": _("Expense Voucher of %s") % rec.name,
                    "narration": rec.comments,
                    "line_ids": account_lines,
                }
            )
            move.action_post()

            rec.write({"payment_entry_id": move.id, "state": "posted"})


class AccountExpenseVoucherLine(models.Model):
    _name = "account.expense.voucher.line"
    _description = "Expense Voucher Line"

    expense_id = fields.Many2one("account.expense.voucher", string="Expense", ondelete="cascade")
    account_id = fields.Many2one("account.account", string="Account", required=True)
    label = fields.Char(string="Label", required=True)
    price_amount = fields.Float(string="Price")
    tax_id = fields.Many2one("account.tax", string="Tax")
    tax_amount = fields.Float(string="Tax Amount", compute="_compute_amount", store=False)
    subtotal = fields.Float(string="Sub Total", compute="_compute_amount", store=False)
    project_id = fields.Many2one("project.project", string="Project")
    currency_id = fields.Many2one(related="expense_id.currency_id", readonly=True)

    @api.onchange("expense_id.voucher_type")
    def _onchange_voucher_type(self):
        if self.expense_id.voucher_type == "send":
            return {"domain": {"tax_id": [("type_tax_use", "=", "purchase")]}}
        if self.expense_id.voucher_type == "receive":
            return {"domain": {"tax_id": [("type_tax_use", "=", "sale")]}}
        return {"domain": {"tax_id": []}}

    @api.depends("price_amount", "tax_id", "expense_id.currency_id")
    def _compute_amount(self):
        for line in self:
            taxes_res = line.tax_id.compute_all(
                line.price_amount,
                currency=line.expense_id.currency_id,
                quantity=1.0,
                product=None,
                partner=line.expense_id.partner_id,
            ) if line.tax_id else {
                "taxes": [],
                "total_included": line.price_amount,
            }
            line.tax_amount = sum(t.get("amount", 0.0) for t in taxes_res.get("taxes", []))
            line.subtotal = taxes_res.get("total_included", line.price_amount)


