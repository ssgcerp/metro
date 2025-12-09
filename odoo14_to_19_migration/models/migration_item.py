# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MigrationItem(models.TransientModel):
    _name = 'odoo14.migration.item'
    _description = 'Migration Item'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'odoo14.migration.wizard',
        string='Migration Wizard',
        required=True,
        ondelete='cascade'
    )
    
    category = fields.Selection([
        ('customers', 'Customers'),
        ('vendors', 'Vendors'),
        ('products', 'Products'),
        ('accounting', 'Accounting'),
    ], string='Category', required=True)
    
    model_name = fields.Char(
        string='Model Name',
        required=True,
        help='Technical name of the model (e.g., res.partner, sale.order)'
    )
    
    display_name = fields.Char(
        string='Display Name',
        required=True,
        help='Human-readable name (e.g., Customers, Quotations)'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order in which items appear'
    )
    
    # Count fields
    total_count = fields.Integer(
        string='Total Count',
        default=0,
        readonly=True,
        help='Total number of records found in Odoo 14'
    )
    
    migrated_count = fields.Integer(
        string='Migrated Count',
        default=0,
        readonly=True,
        help='Number of records successfully migrated'
    )
    
    # Status
    is_checked = fields.Boolean(
        string='Checked',
        default=False,
        readonly=True,
        help='Whether data has been checked'
    )
    
    last_check_date = fields.Datetime(
        string='Last Check Date',
        readonly=True
    )
    
    # Domain for filtering records
    domain = fields.Text(
        string='Domain',
        help='Odoo domain to filter records (JSON format)'
    )
    
    # Fields to fetch
    fields_to_fetch = fields.Text(
        string='Fields to Fetch',
        help='Comma-separated list of fields to fetch from Odoo 14'
    )
    
    def action_check(self):
        """Check data count for this item"""
        self.ensure_one()
        if not self.wizard_id:
            raise UserError('Migration wizard not found.')
        
        # Ensure wizard is saved - save it if it's new
        if not self.wizard_id.id:
            # Save the wizard first
            self.wizard_id = self.wizard_id.create({
                'config_id': self.wizard_id.config_id.id if self.wizard_id.config_id else False,
            })
            # Update our wizard_id reference
            self.write({'wizard_id': self.wizard_id.id})
        
        # Pass self.id as active_id in context
        return self.wizard_id.with_context(active_id=self.id).action_check_item()
    
    def action_preview(self):
        """Preview records for this item"""
        self.ensure_one()
        if not self.wizard_id:
            raise UserError('Migration wizard not found.')
        # Pass self.id as active_id in context
        return self.wizard_id.with_context(active_id=self.id).action_preview_item()
    
    def action_migrate(self):
        """Migrate records for this item"""
        self.ensure_one()
        if not self.wizard_id:
            raise UserError('Migration wizard not found.')
        # Pass self.id as active_id in context
        return self.wizard_id.with_context(active_id=self.id).action_migrate_item()

