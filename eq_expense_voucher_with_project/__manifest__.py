# -*- coding: utf-8 -*-
{
    "name": "Expense Voucher with project",
    "version": "19.0.1.0.0",
    "summary": "Expense Voucher",
    "description": "Expense Voucher",
    "category": "Accounting",
    "author": "Odox Softhub",
    "company": "Odox Softhub LLP",
    "website": "https://www.odoxsofthub.com",
    "license": "AGPL-3",
    "depends": [
        "base",
        "mail",
        "account",
        "project",
    ],
    "data": [
        "data/data.xml",
        "security/ir.model.access.csv",
        "views/expense_voucher_view.xml",
        "report/report.xml",
        "report/expense_voucher_template.xml",
    ],
    "installable": True,
    "application": True,
}
