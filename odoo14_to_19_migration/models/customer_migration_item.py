# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)


class CustomerMigrationItem(models.TransientModel):
    _name = 'odoo14.customer.migration.item'
    _description = 'Customer Migration Item'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'odoo14.customer.migration.wizard',
        string='Migration Wizard',
        required=True,
        ondelete='cascade'
    )
    
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
        if not self.wizard_id or not self.wizard_id.config_id:
            raise UserError('Please select a migration configuration first.')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.wizard_id.config_id.odoo14_url,
                db=self.wizard_id.config_id.odoo14_database,
                username=self.wizard_id.config_id.odoo14_username,
                password=self.wizard_id.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14. Please test the connection first.')
            
            # Map model names to API endpoints
            model_map = {
                'res.partner': 'customers',
                'sale.order': 'quotations' if 'draft' in (self.domain or '').lower() or 'sent' in (self.domain or '').lower() else 'sales_orders',
                'account.move': 'invoices',
                'account.invoice': 'invoices',
            }
            
            # Try REST API first
            api_model = model_map.get(self.model_name)
            if api_model:
                count = client.get_count_rest(api_model)
            else:
                # Fallback to XML-RPC
                domain = json.loads(self.domain) if self.domain else []
                model_name = self.model_name
                if model_name == 'account.move':
                    invoice_model = client._get_invoice_model()
                    if invoice_model:
                        model_name = invoice_model
                        if invoice_model == 'account.invoice':
                            domain = [d if d[0] != 'move_type' else ('type', d[1], d[2]) for d in domain]
                count = client.count(model_name, domain)
            
            self.write({
                'total_count': count,
                'is_checked': True,
                'last_check_date': fields.Datetime.now()
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Data Check Complete',
                    'message': 'Found %s %s records.' % (count, self.display_name),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error("Error checking %s: %s" % (self.display_name, str(e)))
            raise UserError('Error checking %s: %s' % (self.display_name, str(e)))
    
    def action_preview(self):
        """Preview records for this item"""
        self.ensure_one()
        if self.total_count == 0:
            raise UserError(f'No {self.display_name} records found. Please check data first.')
        
        # TODO: Implement preview functionality
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Preview',
                'message': f'Preview functionality for {self.display_name} will be implemented.',
                'type': 'info',
                'sticky': False,
            }
        }
    
    def action_migrate(self):
        """Migrate records for this item"""
        self.ensure_one()
        if self.total_count == 0:
            raise UserError(f'No {self.display_name} records found. Please check data first.')
        
        # TODO: Implement migration functionality
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Migration',
                'message': f'Migration functionality for {self.display_name} will be implemented.',
                'type': 'info',
                'sticky': False,
            }
        }

