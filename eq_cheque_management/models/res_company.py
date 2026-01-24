# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    cheque_config_id = fields.Many2one(
        'eq.cheque.config',
        string='Cheque Configuration',
        compute='_compute_cheque_config_id',
        store=False,
    )

    def _compute_cheque_config_id(self):
        """Compute cheque configuration for company"""
        for company in self:
            company.cheque_config_id = self.env['eq.cheque.config'].search([
                ('company_id', '=', company.id)
            ], limit=1)

