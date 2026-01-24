# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    branch_code = fields.Char(
        string='Branch Code',
        help='Branch code used in AMC contract number generation (e.g., AUH, DXB, SHJ, FUJ)',
        size=10,
        translate=False
    )
