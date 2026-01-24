# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class BranchCompanyMapping(models.Model):
    _name = 'odoo14.branch.company.mapping'
    _description = 'Odoo 14 Branch to Odoo 19 Company Mapping'
    _order = 'odoo14_branch_id, odoo14_branch_name'
    
    @api.depends('odoo14_branch_id', 'odoo14_branch_name')
    def _compute_display_name(self):
        """Display name: Branch ID or Branch Name"""
        for record in self:
            if record.odoo14_branch_id:
                record.display_name = f"Branch ID: {record.odoo14_branch_id}"
            elif record.odoo14_branch_name:
                record.display_name = f"Branch: {record.odoo14_branch_name}"
            else:
                record.display_name = "Branch Mapping"
    
    display_name = fields.Char(compute='_compute_display_name', store=False)

    odoo14_branch_id = fields.Integer(
        string='Odoo 14 Branch ID',
        help='ID of the branch in Odoo 14 (optional if branch name is provided)'
    )
    
    odoo14_branch_name = fields.Char(
        string='Odoo 14 Branch Name',
        help='Name of the branch in Odoo 14 (optional if branch ID is provided)'
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

    # Note: Using Python constraints instead of _sql_constraints for Odoo 19 compatibility
    # SQL constraints with nullable fields can be problematic, so we use Python validation
    @api.constrains('odoo14_branch_id', 'odoo14_branch_name', 'odoo19_company_id')
    def _check_branch_fields(self):
        """Ensure at least one of branch ID or name is provided and check uniqueness"""
        for record in self:
            if not record.odoo14_branch_id and not record.odoo14_branch_name:
                raise ValidationError('Either Odoo 14 Branch ID or Branch Name must be provided.')
            if record.odoo14_branch_id and record.odoo14_branch_id <= 0:
                raise ValidationError('Odoo 14 Branch ID must be a positive number if provided.')
            
            # Check uniqueness: branch_id + company combination
            if record.odoo14_branch_id:
                existing = self.search([
                    ('odoo14_branch_id', '=', record.odoo14_branch_id),
                    ('odoo19_company_id', '=', record.odoo19_company_id.id),
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ], limit=1)
                if existing:
                    raise ValidationError(f'Branch ID {record.odoo14_branch_id} is already mapped to company {record.odoo19_company_id.name}.')
            
            # Check uniqueness: branch_name + company combination
            if record.odoo14_branch_name:
                existing = self.search([
                    ('odoo14_branch_name', '=', record.odoo14_branch_name),
                    ('odoo19_company_id', '=', record.odoo19_company_id.id),
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ], limit=1)
                if existing:
                    raise ValidationError(f'Branch Name "{record.odoo14_branch_name}" is already mapped to company {record.odoo19_company_id.name}.')

    @api.model
    def get_company_for_branch(self, odoo14_branch_id=None, odoo14_branch_name=None):
        """
        Get the mapped Odoo 19 company for a given Odoo 14 branch ID or name.
        
        Args:
            odoo14_branch_id: ID of the branch in Odoo 14 (optional)
            odoo14_branch_name: Name of the branch in Odoo 14 (optional)
        
        Returns:
            The company record or False if not mapped.
        
        Priority:
            1. Try to find by branch_id if provided
            2. Try to find by branch_name if provided and branch_id not found
        """
        # Priority 1: Try to find by branch_id if provided
        if odoo14_branch_id:
            mapping = self.search([
                ('odoo14_branch_id', '=', odoo14_branch_id),
                ('active', '=', True)
            ], limit=1)
            
            if mapping and mapping.odoo19_company_id:
                return mapping.odoo19_company_id
        
        # Priority 2: Try to find by branch_name if provided and branch_id not found
        if odoo14_branch_name:
            mapping = self.search([
                ('odoo14_branch_name', '=', odoo14_branch_name),
                ('active', '=', True)
            ], limit=1)
            
            if mapping and mapping.odoo19_company_id:
                return mapping.odoo19_company_id
        
        return False
