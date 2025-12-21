# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class BranchCompanyMapping(models.Model):
    _name = 'odoo14.branch.company.mapping'
    _description = 'Odoo 14 Branch to Odoo 19 Company Mapping'
    _rec_name = 'odoo14_branch_id'
    _order = 'odoo14_branch_id'

    odoo14_branch_id = fields.Integer(
        string='Odoo 14 Branch ID',
        required=True,
        help='ID of the branch in Odoo 14'
    )
    
    odoo19_company_id = fields.Many2one(
        'res.company',
        string='Odoo 19 Company',
        required=True,
        ondelete='restrict',
        help='Company in Odoo 19 to map this branch to'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to disable this mapping without deleting it'
    )

    _sql_constraints = [
        ('unique_branch_company', 'unique(odoo14_branch_id, odoo19_company_id)', 
         'Each branch can only be mapped once to each company!'),
    ]

    @api.constrains('odoo14_branch_id')
    def _check_branch_id(self):
        """Ensure branch ID is valid"""
        for record in self:
            if record.odoo14_branch_id <= 0:
                raise ValidationError('Odoo 14 Branch ID must be a positive number.')

    @api.model
    def get_company_for_branch(self, odoo14_branch_id):
        """
        Get the mapped Odoo 19 company for a given Odoo 14 branch ID.
        Returns the company record or False if not mapped.
        """
        mapping = self.search([
            ('odoo14_branch_id', '=', odoo14_branch_id),
            ('active', '=', True)
        ], limit=1)
        
        if mapping and mapping.odoo19_company_id:
            return mapping.odoo19_company_id
        return False
