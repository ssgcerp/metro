# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


def _log_failed_system_type_migration(system_type_name, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        # Get log directory (use module directory/logs)
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_system_type_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {system_type_name} | {error_detail[:200]}\n")
        
        _logger.info("Failed system type migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed migrations log: %s", str(e))


class AMCSystemTypeMigrationLine(models.Model):
    """Model to store uploaded system type names and track migration status"""
    _name = 'amc.system.type.migration.line'
    _description = 'AMC System Type Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    uploaded_system_type_name = fields.Char(
        string='System Type Name',
        required=True,
        index=True,
        help='System type name from Excel upload'
    )
    
    in_system_system_type_name = fields.Char(
        string='In-System System Type Name',
        readonly=True,
        help='Actual system type name found in Odoo 14 or Odoo 19'
    )
    
    status = fields.Selection([
        ('already_migrated', 'Already Migrated'),
        ('pending_migration', 'Pending Migration'),
        ('queued', 'Queued'),
        ('not_found', 'Not Found'),
        ('migrating', 'Migrating'),
        ('migrated', 'Migrated'),
        ('error', 'Error'),
    ], string='Status', default='pending_migration', readonly=True, index=True, tracking=True)
    
    status_message = fields.Text(string='Status Message', readonly=True)
    
    error_message = fields.Text(string='Error Message', readonly=True)
    
    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=False,
        help='Optional: Odoo 14 connection configuration for status checking and migration'
    )
    
    odoo14_system_type_id = fields.Integer(
        string='Odoo 14 System Type ID',
        readonly=True,
        help='ID of system type in Odoo 14 if found'
    )
    
    odoo19_system_type_id = fields.Many2one(
        'fm.amc.system.type',
        string='Odoo 19 System Type',
        readonly=True,
        help='Migrated system type in Odoo 19'
    )
    
    migration_date = fields.Datetime(
        string='Migration Date',
        readonly=True,
        help='Date and time when migration was completed'
    )

    def action_open_upload_wizard(self):
        """Open the Excel upload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'amc.system.type.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_config_id': self.config_id.id if self.config_id else False,
            }
        }

    def action_bulk_migrate(self):
        """Bulk migrate selected system types - only sets status to Queued"""
        try:
            pending = self.filtered(lambda l: l.status == 'pending_migration')
            if not pending:
                raise UserError('No system types with "Pending Migration" status selected')

            pending_ids = pending.ids

            # Mark all records as "queued" before processing
            fresh_pending = self.env['amc.system.type.migration.line'].browse(pending_ids)
            for record in fresh_pending:
                record.write({
                    'status': 'queued',
                    'status_message': 'Queued for migration - waiting to be processed...',
                    'error_message': False,  # Clear any previous error messages
                })
            self.env.cr.commit()
            _logger.info("✅ Marked %s system types as 'queued'", len(fresh_pending))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'System Types Queued',
                    'message': f'Queued {len(pending_ids)} system types for migration. Use PowerShell script or HTTP route to start processing.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except UserError as ue:
            raise ue
        except Exception as e:
            error_msg = str(e)
            _logger.error("Unexpected error in action_bulk_migrate: %s", error_msg, exc_info=True)
            # Attempt to revert status to pending_migration if possible, or keep as is
            if 'pending_ids' in locals() and pending_ids:
                fresh_pending = self.env['amc.system.type.migration.line'].browse(pending_ids)
                fresh_pending.write({
                    'status': 'pending_migration',
                    'status_message': f'Failed to queue (unexpected error): {error_msg[:200]}',
                    'error_message': error_msg[:500],
                })
                self.env.cr.commit()
            raise UserError(f'An unexpected error occurred while queuing system types: {error_msg}')

    def action_check_status(self):
        """Check if system type exists in Odoo 14 or Odoo 19"""
        self.ensure_one()
        
        if not self.config_id:
            raise UserError('Please select a Migration Configuration to check status')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14')
            
            # Search in Odoo 14
            odoo14_system_types = client.search(
                'amc.system.type',
                [('name', '=', self.uploaded_system_type_name)],
                limit=1
            )
            
            # Search in Odoo 19
            odoo19_system_types = self.env['fm.amc.system.type'].search([
                ('name', '=', self.uploaded_system_type_name)
            ], limit=1)
            
            if odoo19_system_types:
                self.write({
                    'status': 'already_migrated',
                    'status_message': f'System type already exists in Odoo 19',
                    'in_system_system_type_name': self.uploaded_system_type_name,
                    'odoo19_system_type_id': odoo19_system_types[0].id,
                })
            elif odoo14_system_types:
                self.write({
                    'status': 'pending_migration',
                    'status_message': f'Found in Odoo 14 (ID: {odoo14_system_types[0]})',
                    'in_system_system_type_name': self.uploaded_system_type_name,
                    'odoo14_system_type_id': odoo14_system_types[0],
                })
            else:
                self.write({
                    'status': 'not_found',
                    'status_message': 'System type not found in Odoo 14 or Odoo 19',
                    'in_system_system_type_name': False,
                })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Status Check Complete',
                    'message': f'Status updated for {self.uploaded_system_type_name}',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error checking status: %s", error_msg, exc_info=True)
            self.write({
                'status': 'error',
                'status_message': f'Error checking status: {error_msg[:200]}',
                'error_message': error_msg[:500],
            })
            raise UserError(f'Error checking status: {error_msg}')

    def action_migrate(self):
        """Migrate system type from Odoo 14 to Odoo 19"""
        self.ensure_one()
        
        if not self.config_id:
            raise UserError('Please select a Migration Configuration to migrate')
        
        if self.status == 'already_migrated':
            raise UserError('This system type is already migrated')
        
        if self.status == 'migrated':
            raise UserError('This system type has already been migrated')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14')
            
            # Mark as migrating
            self.write({
                'status': 'migrating',
                'status_message': 'Starting migration...',
                'error_message': False,
            })
            self.env.cr.commit()
            
            # Fetch system type data from Odoo 14
            system_type_data = client.search_read(
                'amc.system.type',
                [('id', '=', self.odoo14_system_type_id)] if self.odoo14_system_type_id else [('name', '=', self.uploaded_system_type_name)],
                ['name', 'number', 'times', 'description', 'system_type_line_ids'],
                limit=1
            )
            
            if not system_type_data:
                raise UserError(f'System type "{self.uploaded_system_type_name}" not found in Odoo 14')
            
            system_type_info = system_type_data[0]
            
            # Prepare values for Odoo 19
            # Map fields: name, number, times, description
            # Note: Odoo 14 number is Char, Odoo 19 is Integer
            number_value = system_type_info.get('number', '')
            try:
                number_int = int(number_value) if number_value else 1
            except (ValueError, TypeError):
                number_int = 1
            
            # Map times (Odoo 14 only has 'times_in_year', Odoo 19 has more options)
            times_value = system_type_info.get('times', 'times_in_year')
            
            # Map description (Odoo 14 is Text, Odoo 19 is Html)
            description_value = system_type_info.get('description', '') or ''
            
            # Create system type in Odoo 19
            system_type_vals = {
                'name': system_type_info.get('name', ''),
                'number': number_int,
                'times': times_value,
                'description': description_value,
                'active': True,
            }
            
            system_type = self.env['fm.amc.system.type'].create(system_type_vals)
            _logger.info("Created system type %s (ID: %s)", system_type.name, system_type.id)
            
            # Migrate devices (system_type_line_ids)
            if system_type_info.get('system_type_line_ids'):
                device_line_ids = system_type_info['system_type_line_ids']
                if isinstance(device_line_ids, (list, tuple)):
                    for line_id in device_line_ids:
                        try:
                            # Fetch line data from Odoo 14
                            line_data = client.search_read(
                                'amc.system.type.lines',
                                [('id', '=', line_id)],
                                ['product_id', 'quantity', 'unit', 'uom_id'],
                                limit=1
                            )
                            
                            if line_data:
                                line_info = line_data[0]
                                
                                # Find or create product in Odoo 19
                                product = None
                                if line_info.get('product_id'):
                                    product_id = line_info['product_id']
                                    if isinstance(product_id, (list, tuple)) and len(product_id) > 0:
                                        product_id = product_id[0]
                                    
                                    # Try to find by ID first
                                    product = self.env['product.product'].search([('id', '=', product_id)], limit=1)
                                    
                                    # If not found, try to get from Odoo 14 and find by default_code or name
                                    if not product:
                                        try:
                                            product_data = client.search_read(
                                                'product.product',
                                                [('id', '=', product_id)],
                                                ['name', 'default_code', 'barcode'],
                                                limit=1
                                            )
                                            if product_data:
                                                prod_data = product_data[0]
                                                # Try to find by default_code
                                                if prod_data.get('default_code'):
                                                    product = self.env['product.product'].search([
                                                        ('default_code', '=', prod_data['default_code'])
                                                    ], limit=1)
                                                
                                                # If still not found, try by name
                                                if not product and prod_data.get('name'):
                                                    product = self.env['product.product'].search([
                                                        ('name', '=', prod_data['name'])
                                                    ], limit=1)
                                                
                                                # If still not found, try by barcode
                                                if not product and prod_data.get('barcode'):
                                                    product = self.env['product.product'].search([
                                                        ('barcode', '=', prod_data['barcode'])
                                                    ], limit=1)
                                                
                                                # If still not found, create a basic product
                                                if not product:
                                                    product_vals = {
                                                        'name': prod_data.get('name', 'Migrated Product'),
                                                        'type': 'consu',  # Consumable
                                                    }
                                                    if prod_data.get('default_code'):
                                                        product_vals['default_code'] = prod_data['default_code']
                                                    product = self.env['product.product'].create(product_vals)
                                                    _logger.info("Created product %s for system type device", product.name)
                                        except Exception as e:
                                            _logger.warning("Could not migrate product %s: %s", product_id, str(e))
                                
                                if product:
                                    # Create device line in Odoo 19
                                    device_vals = {
                                        'system_type_id': system_type.id,
                                        'product_id': product.id,
                                        'quantity': line_info.get('quantity', 0.0) or 0.0,
                                    }
                                    self.env['fm.amc.system.type.device'].create(device_vals)
                                    _logger.info("Created device line for product %s", product.name)
                                else:
                                    _logger.warning("Product not found for device line, skipping")
                                    
                        except Exception as e:
                            _logger.warning("Error migrating device line %s: %s", line_id, str(e))
                            continue
            
            # Update status
            self.write({
                'status': 'migrated',
                'status_message': f'Successfully migrated to Odoo 19',
                'odoo19_system_type_id': system_type.id,
                'migration_date': fields.Datetime.now(),
                'in_system_system_type_name': system_type.name,
            })
            self.env.cr.commit()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Migration Complete',
                    'message': f'System type "{system_type.name}" migrated successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except UserError:
            raise
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error migrating system type: %s", error_msg, exc_info=True)
            _log_failed_system_type_migration(self.uploaded_system_type_name, error_msg)
            
            self.write({
                'status': 'error',
                'status_message': f'Migration failed: {error_msg[:200]}',
                'error_message': error_msg[:500],
            })
            self.env.cr.commit()
            
            raise UserError(f'Error migrating system type: {error_msg}')

