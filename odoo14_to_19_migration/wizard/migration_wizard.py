# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime
import json

_logger = logging.getLogger(__name__)


class MigrationWizard(models.TransientModel):
    _name = 'odoo14.migration.wizard'
    _description = 'Odoo 14 to Odoo 19 Migration Wizard'

    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=True,
        help='Select the Odoo 14 connection configuration'
    )
    
    # Migration items (one2many)
    customer_items = fields.One2many(
        'odoo14.migration.item',
        'wizard_id',
        string='Customer Items',
        domain=[('category', '=', 'customers')]
    )
    
    vendor_items = fields.One2many(
        'odoo14.migration.item',
        'wizard_id',
        string='Vendor Items',
        domain=[('category', '=', 'vendors')]
    )
    
    product_items = fields.One2many(
        'odoo14.migration.item',
        'wizard_id',
        string='Product Items',
        domain=[('category', '=', 'products')]
    )
    
    accounting_items = fields.One2many(
        'odoo14.migration.item',
        'wizard_id',
        string='Accounting Items',
        domain=[('category', '=', 'accounting')]
    )
    
    # Legacy fields (kept for backward compatibility)
    migrate_invoices = fields.Boolean(
        string='Migrate Customer Invoices',
        default=True,
        help='Migrate customer invoices (out_invoice)'
    )
    migrate_purchase_invoices = fields.Boolean(
        string='Migrate Vendor Bills',
        default=True,
        help='Migrate vendor bills (in_invoice)'
    )
    
    # Data preview fields
    invoice_count = fields.Integer(
        string='Invoices Found',
        readonly=True,
        default=0
    )
    purchase_invoice_count = fields.Integer(
        string='Vendor Bills Found',
        readonly=True,
        default=0
    )
    
    # Migration status
    migration_status = fields.Text(
        string='Migration Status',
        readonly=True
    )
    migration_progress = fields.Float(
        string='Migration Progress (%)',
        readonly=True,
        default=0.0
    )
    is_migrating = fields.Boolean(
        string='Migration in Progress',
        readonly=True,
        default=False
    )
    
    # Migration results
    invoices_migrated = fields.Integer(
        string='Invoices Migrated',
        readonly=True,
        default=0
    )
    purchase_invoices_migrated = fields.Integer(
        string='Vendor Bills Migrated',
        readonly=True,
        default=0
    )
    errors_count = fields.Integer(
        string='Errors',
        readonly=True,
        default=0
    )
    error_log = fields.Text(
        string='Error Log',
        readonly=True
    )
    
    @api.model
    def create(self, vals):
        """Create wizard and initialize migration items"""
        wizard = super().create(vals)
        wizard._initialize_migration_items()
        return wizard
    
    def _initialize_migration_items(self):
        """Initialize default migration items"""
        # Check if items already exist
        if self.customer_items or self.vendor_items or self.product_items or self.accounting_items:
            return
        
        # Define default migration items
        default_items = [
            # Customer category
            {'category': 'customers', 'model_name': 'res.partner', 'display_name': 'Customers', 
             'sequence': 10, 'domain': "[('customer_rank', '>', 0)]", 
             'fields_to_fetch': 'name,email,phone,mobile,street,street2,city,state_id,zip,country_id,vat,is_company,customer_rank'},
            {'category': 'customers', 'model_name': 'sale.order', 'display_name': 'Quotations', 
             'sequence': 20, 'domain': "[('state', 'in', ['draft', 'sent', 'sale'])]", 
             'fields_to_fetch': 'name,partner_id,date_order,state,amount_total,amount_untaxed,amount_tax'},
            {'category': 'customers', 'model_name': 'sale.order', 'display_name': 'Sales Orders', 
             'sequence': 30, 'domain': "[('state', '=', 'sale')]", 
             'fields_to_fetch': 'name,partner_id,date_order,state,amount_total,amount_untaxed,amount_tax'},
            {'category': 'customers', 'model_name': 'account.move', 'display_name': 'Invoices', 
             'sequence': 40, 'domain': "[('move_type', '=', 'out_invoice')]", 
             'fields_to_fetch': 'name,partner_id,invoice_date,invoice_date_due,state,amount_total,amount_untaxed,amount_tax'},
            {'category': 'customers', 'model_name': 'account.payment', 'display_name': 'Payments', 
             'sequence': 50, 'domain': "[('partner_type', '=', 'customer')]", 
             'fields_to_fetch': 'name,partner_id,payment_type,amount,date,state'},
            {'category': 'customers', 'model_name': 'account.journal', 'display_name': 'Journals', 
             'sequence': 60, 'domain': "[('type', 'in', ['sale', 'bank', 'cash'])]", 
             'fields_to_fetch': 'name,code,type,currency_id'},
            
            # Vendor category
            {'category': 'vendors', 'model_name': 'res.partner', 'display_name': 'Vendors', 
             'sequence': 10, 'domain': "[('supplier_rank', '>', 0)]", 
             'fields_to_fetch': 'name,email,phone,mobile,street,street2,city,state_id,zip,country_id,vat,is_company,supplier_rank'},
            {'category': 'vendors', 'model_name': 'purchase.order', 'display_name': 'Purchase Orders', 
             'sequence': 20, 'domain': "[]", 
             'fields_to_fetch': 'name,partner_id,date_order,state,amount_total,amount_untaxed,amount_tax'},
            {'category': 'vendors', 'model_name': 'account.move', 'display_name': 'Vendor Bills', 
             'sequence': 30, 'domain': "[('move_type', '=', 'in_invoice')]", 
             'fields_to_fetch': 'name,partner_id,invoice_date,invoice_date_due,state,amount_total,amount_untaxed,amount_tax'},
            {'category': 'vendors', 'model_name': 'account.payment', 'display_name': 'Payments', 
             'sequence': 40, 'domain': "[('partner_type', '=', 'supplier')]", 
             'fields_to_fetch': 'name,partner_id,payment_type,amount,date,state'},
            
            # Product category
            {'category': 'products', 'model_name': 'product.product', 'display_name': 'Products', 
             'sequence': 10, 'domain': "[]", 
             'fields_to_fetch': 'name,default_code,barcode,list_price,standard_price,categ_id,uom_id,type,sale_ok,purchase_ok'},
            {'category': 'products', 'model_name': 'product.category', 'display_name': 'Product Categories', 
             'sequence': 20, 'domain': "[]", 
             'fields_to_fetch': 'name,parent_id'},
            
            # Accounting category
            {'category': 'accounting', 'model_name': 'account.account', 'display_name': 'Accounts', 
             'sequence': 10, 'domain': "[]", 
             'fields_to_fetch': 'name,code,account_type,company_id'},
            {'category': 'accounting', 'model_name': 'account.journal', 'display_name': 'Journals', 
             'sequence': 20, 'domain': "[]", 
             'fields_to_fetch': 'name,code,type,currency_id'},
            {'category': 'accounting', 'model_name': 'account.tax', 'display_name': 'Taxes', 
             'sequence': 30, 'domain': "[]", 
             'fields_to_fetch': 'name,amount,amount_type,type_tax_use'},
        ]
        
        # Create migration items if they don't exist
        if 'customer_items' in fields_list or not fields_list:
            customer_items = []
            vendor_items = []
            product_items = []
            accounting_items = []
            
            for item_data in default_items:
                item_vals = {
                    'category': item_data['category'],
                    'model_name': item_data['model_name'],
                    'display_name': item_data['display_name'],
                    'sequence': item_data['sequence'],
                    'domain': item_data.get('domain', '[]'),
                    'fields_to_fetch': item_data.get('fields_to_fetch', ''),
                }
                
                if item_data['category'] == 'customers':
                    customer_items.append((0, 0, item_vals))
                elif item_data['category'] == 'vendors':
                    vendor_items.append((0, 0, item_vals))
                elif item_data['category'] == 'products':
                    product_items.append((0, 0, item_vals))
                elif item_data['category'] == 'accounting':
                    accounting_items.append((0, 0, item_vals))
            
        # Create the items
        if customer_items:
            self.write({'customer_items': customer_items})
        if vendor_items:
            self.write({'vendor_items': vendor_items})
        if product_items:
            self.write({'product_items': product_items})
        if accounting_items:
            self.write({'accounting_items': accounting_items})
    
    @api.model
    def default_get(self, fields_list):
        """Initialize default migration items"""
        res = super().default_get(fields_list)
        # Don't create items in default_get, let create() handle it
        return res
    
    def action_check_item(self):
        """Check data count for a specific migration item"""
        self.ensure_one()
        # Get active_id from context (the migration item record)
        active_id = self.env.context.get('active_id')
        if not active_id:
            raise UserError('Item ID not found in context.')
        item = self.env['odoo14.migration.item'].browse(active_id)
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14. Please test the connection first.')
            
            # Parse domain
            domain = json.loads(item.domain) if item.domain else []
            
            # Handle special case for account.move (need to check which model exists)
            model_name = item.model_name
            if model_name == 'account.move':
                invoice_model = client._get_invoice_model()
                if invoice_model:
                    model_name = invoice_model
                    # Adjust domain for account.invoice
                    if invoice_model == 'account.invoice':
                        # Convert move_type to type
                        domain = [d if d[0] != 'move_type' else ('type', d[1], d[2]) for d in domain]
            
            # Count records
            count = client.count(model_name, domain)
            
            item.write({
                'total_count': count,
                'is_checked': True,
                'last_check_date': fields.Datetime.now()
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Data Check Complete',
                    'message': f'Found {count} {item.display_name} records.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error checking {item.display_name}: {str(e)}")
            raise UserError(f'Error checking {item.display_name}: {str(e)}')
    
    def action_preview_item(self):
        """Preview records for a specific migration item"""
        self.ensure_one()
        # Get active_id from context (the migration item record)
        active_id = self.env.context.get('active_id')
        if not active_id:
            raise UserError('Item ID not found in context.')
        item = self.env['odoo14.migration.item'].browse(active_id)
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        if item.total_count == 0:
            raise UserError(f'No {item.display_name} records found. Please check data first.')
        
        # For now, show a notification. Later we can create a preview window
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Preview',
                'message': f'Preview functionality for {item.display_name} will be implemented.',
                'type': 'info',
                'sticky': False,
            }
        }
    
    def action_migrate_item(self):
        """Migrate records for a specific migration item"""
        self.ensure_one()
        # Get active_id from context (the migration item record)
        active_id = self.env.context.get('active_id')
        if not active_id:
            raise UserError('Item ID not found in context.')
        item = self.env['odoo14.migration.item'].browse(active_id)
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        if item.total_count == 0:
            raise UserError(f'No {item.display_name} records found. Please check data first.')
        
        # For now, show a notification. Later we can implement actual migration
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Migration',
                'message': f'Migration functionality for {item.display_name} will be implemented.',
                'type': 'info',
                'sticky': False,
            }
        }
    
    def action_view_invoices(self):
        """View invoice records from Odoo 14 in a popup"""
        self.ensure_one()
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14. Please test the connection first.')
            
            # Get invoice model
            invoice_model = client._get_invoice_model()
            
            # Get invoices (limit to 500 for preview)
            invoices = client.get_invoices(invoice_model=invoice_model, limit=500)
            purchase_invoices = client.get_purchase_invoices(invoice_model=invoice_model, limit=500)
            
            # Clear existing preview records
            self.env['odoo14.invoice.preview'].search([]).unlink()
            
            # Create preview records
            preview_records = []
            import json
            
            # Process customer invoices
            for inv in invoices:
                partner_id = inv.get('partner_id')
                partner_name = 'Unknown'
                partner_address = ''
                if partner_id:
                    if isinstance(partner_id, list):
                        partner_id_val = partner_id[0] if partner_id else None
                    else:
                        partner_id_val = partner_id
                    if partner_id_val:
                        partner = client.get_partner(partner_id_val)
                        if partner:
                            partner_name = partner.get('name', 'Unknown')
                            # Build address
                            address_parts = []
                            if partner.get('street'):
                                address_parts.append(partner.get('street'))
                            if partner.get('street2'):
                                address_parts.append(partner.get('street2'))
                            if partner.get('city'):
                                address_parts.append(partner.get('city'))
                            if partner.get('zip'):
                                address_parts.append(partner.get('zip'))
                            if partner.get('country_id'):
                                country = self.env['res.country'].browse(partner['country_id'][0] if isinstance(partner['country_id'], list) else partner['country_id'])
                                if country.exists():
                                    address_parts.append(country.name)
                            partner_address = ', '.join(address_parts)
                
                currency_name = ''
                currency_id = inv.get('currency_id')
                if currency_id:
                    if isinstance(currency_id, list):
                        currency_id_val = currency_id[0] if currency_id else None
                    else:
                        currency_id_val = currency_id
                    if currency_id_val:
                        currency = client.get_currency(currency_id_val)
                        if currency:
                            currency_name = currency.get('name', '')
                
                journal_name = ''
                journal_id = inv.get('journal_id')
                if journal_id:
                    if isinstance(journal_id, list):
                        journal_id_val = journal_id[0] if journal_id else None
                    else:
                        journal_id_val = journal_id
                    if journal_id_val:
                        journal = client.get_journal(journal_id_val)
                        if journal:
                            journal_name = journal.get('name', '')
                
                invoice_date = inv.get('invoice_date') or inv.get('date_invoice')
                date_due = inv.get('invoice_date_due') or inv.get('date_due')
                comment = inv.get('comment') or inv.get('narration', '')
                
                # Get invoice lines using invoice ID (not line IDs)
                invoice_id = inv.get('id')
                invoice_lines = []
                if invoice_id:
                    try:
                        # Get invoice model to determine line model
                        invoice_model = client._get_invoice_model()
                        lines = client.get_invoice_lines(invoice_id, invoice_model)
                        if lines:
                            invoice_lines = lines[:50]  # Limit to 50 lines
                    except Exception as e:
                        _logger.warning(f"Error fetching invoice lines for invoice {invoice_id}: {str(e)}")
                        pass
                
                preview_data = {
                    'name': inv.get('name', ''),
                    'partner_name': partner_name,
                    'partner_address': partner_address,
                    'invoice_date': invoice_date,
                    'date_due': date_due,
                    'amount_total': inv.get('amount_total', 0.0),
                    'amount_untaxed': inv.get('amount_untaxed', 0.0),
                    'amount_tax': inv.get('amount_tax', 0.0),
                    'state': inv.get('state', ''),
                    'invoice_type': 'out_invoice',
                    'currency_name': currency_name,
                    'journal_name': journal_name,
                    'comment': comment,
                    'invoice_line_data': json.dumps(invoice_lines),
                    'invoice_data_json': json.dumps(inv),
                }
                preview_records.append((preview_data, invoice_lines))
            
            # Process purchase invoices
            for inv in purchase_invoices:
                partner_id = inv.get('partner_id')
                partner_name = 'Unknown'
                partner_address = ''
                if partner_id:
                    if isinstance(partner_id, list):
                        partner_id_val = partner_id[0] if partner_id else None
                    else:
                        partner_id_val = partner_id
                    if partner_id_val:
                        partner = client.get_partner(partner_id_val)
                        if partner:
                            partner_name = partner.get('name', 'Unknown')
                            # Build address
                            address_parts = []
                            if partner.get('street'):
                                address_parts.append(partner.get('street'))
                            if partner.get('street2'):
                                address_parts.append(partner.get('street2'))
                            if partner.get('city'):
                                address_parts.append(partner.get('city'))
                            if partner.get('zip'):
                                address_parts.append(partner.get('zip'))
                            if partner.get('country_id'):
                                country = self.env['res.country'].browse(partner['country_id'][0] if isinstance(partner['country_id'], list) else partner['country_id'])
                                if country.exists():
                                    address_parts.append(country.name)
                            partner_address = ', '.join(address_parts)
                
                currency_name = ''
                currency_id = inv.get('currency_id')
                if currency_id:
                    if isinstance(currency_id, list):
                        currency_id_val = currency_id[0] if currency_id else None
                    else:
                        currency_id_val = currency_id
                    if currency_id_val:
                        currency = client.get_currency(currency_id_val)
                        if currency:
                            currency_name = currency.get('name', '')
                
                journal_name = ''
                journal_id = inv.get('journal_id')
                if journal_id:
                    if isinstance(journal_id, list):
                        journal_id_val = journal_id[0] if journal_id else None
                    else:
                        journal_id_val = journal_id
                    if journal_id_val:
                        journal = client.get_journal(journal_id_val)
                        if journal:
                            journal_name = journal.get('name', '')
                
                invoice_date = inv.get('invoice_date') or inv.get('date_invoice')
                date_due = inv.get('invoice_date_due') or inv.get('date_due')
                comment = inv.get('comment') or inv.get('narration', '')
                
                # Get invoice lines using invoice ID (not line IDs)
                invoice_id = inv.get('id')
                invoice_lines = []
                if invoice_id:
                    try:
                        # Get invoice model to determine line model
                        invoice_model = client._get_invoice_model()
                        lines = client.get_invoice_lines(invoice_id, invoice_model)
                        if lines:
                            invoice_lines = lines[:50]  # Limit to 50 lines
                    except Exception as e:
                        _logger.warning(f"Error fetching invoice lines for invoice {invoice_id}: {str(e)}")
                        pass
                
                preview_data = {
                    'name': inv.get('name', ''),
                    'partner_name': partner_name,
                    'partner_address': partner_address,
                    'invoice_date': invoice_date,
                    'date_due': date_due,
                    'amount_total': inv.get('amount_total', 0.0),
                    'amount_untaxed': inv.get('amount_untaxed', 0.0),
                    'amount_tax': inv.get('amount_tax', 0.0),
                    'state': inv.get('state', ''),
                    'invoice_type': 'in_invoice',
                    'currency_name': currency_name,
                    'journal_name': journal_name,
                    'comment': comment,
                    'invoice_line_data': json.dumps(invoice_lines),
                    'invoice_data_json': json.dumps(inv),
                }
                preview_records.append((preview_data, invoice_lines))
            
            # Create preview records with invoice lines
            created_records = []
            if preview_records:
                for preview_data, invoice_lines in preview_records:
                    # Create invoice preview
                    invoice_preview = self.env['odoo14.invoice.preview'].create(preview_data)
                    created_records.append(invoice_preview)
                    
                    # Create invoice line previews
                    line_preview_records = []
                    for idx, line in enumerate(invoice_lines, 1):
                        # Get product name
                        product_name = ''
                        product_id = line.get('product_id')
                        if product_id:
                            if isinstance(product_id, list) and len(product_id) > 1:
                                product_name = product_id[1]
                            elif isinstance(product_id, (int, float)):
                                try:
                                    product = client.get_product(int(product_id))
                                    if product:
                                        product_name = product.get('name', '')
                                except:
                                    pass
                        
                        # Get tax names
                        tax_names = []
                        tax_ids = line.get('tax_ids', [])
                        for tax_id in tax_ids:
                            if isinstance(tax_id, list) and len(tax_id) > 1:
                                tax_names.append(tax_id[1])
                            elif isinstance(tax_id, (int, float)):
                                # Try to get tax name from Odoo 14
                                try:
                                    tax_records = client.read('account.tax', [int(tax_id)], fields=['name'])
                                    if tax_records:
                                        tax_names.append(tax_records[0].get('name', ''))
                                except:
                                    pass
                        
                        line_preview_records.append({
                            'invoice_preview_id': invoice_preview.id,
                            'product_name': product_name,
                            'name': line.get('name', ''),
                            'quantity': line.get('quantity', 0.0),
                            'price_unit': line.get('price_unit', 0.0),
                            'discount': line.get('discount', 0.0),
                            'tax_names': ', '.join(tax_names),
                            'price_subtotal': line.get('price_subtotal', 0.0),
                            'sequence': line.get('sequence', idx * 10),
                        })
                    
                    if line_preview_records:
                        self.env['odoo14.invoice.line.preview'].create(line_preview_records)
            
            # Get first record ID
            first_record_id = created_records[0].id if created_records else False
            
            if not first_record_id:
                raise UserError('No invoices found to preview.')
            
            return {
                'type': 'ir.actions.act_window',
                'name': f'Invoice Preview from Odoo 14 ({len(created_records)} records)',
                'res_model': 'odoo14.invoice.preview',
                'view_mode': 'form',
                'target': 'new',
                'res_id': first_record_id,
            }
        except Exception as e:
            _logger.error(f"Error viewing invoices: {str(e)}")
            raise UserError(f'Error viewing invoices: {str(e)}')

    def action_check_data(self):
        """Check and preview data count from Odoo 14"""
        self.ensure_one()
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14. Please test the connection first.')
            
            # Get Odoo version for better error messages
            odoo_version = client.get_odoo_version()
            version_info = f" (Detected version: {odoo_version})" if odoo_version else ""
            
            # Determine which model to use based on version
            invoice_model = 'account.invoice'
            
            # Parse version to get major version number
            major_version = None
            if odoo_version:
                try:
                    # Extract major version (e.g., "14.0" from "14.0-20231205")
                    version_parts = odoo_version.split('.')
                    if version_parts:
                        major_version = int(version_parts[0])
                except:
                    pass
            
            # Check model existence
            invoice_exists = client.check_model_exists('account.invoice')
            move_exists = client.check_model_exists('account.move')
            
            # If version is 14.x, prefer account.invoice
            if major_version == 14:
                if invoice_exists:
                    invoice_model = 'account.invoice'
                elif move_exists:
                    # Odoo 14 might have both or only account.move in some cases
                    # Try to use account.move but warn the user
                    invoice_model = 'account.move'
                    _logger.warning(f"Odoo 14 instance uses account.move instead of account.invoice")
                else:
                    raise UserError(
                        f'Model "account.invoice" not found in Odoo 14 instance{version_info}.\n\n'
                        'Please verify:\n'
                        '1. The account module is installed in your Odoo 14 instance\n'
                        '2. Your user has proper access rights to view invoices\n'
                        f'3. You are connecting to the correct Odoo instance (URL: {self.config_id.odoo14_url})'
                    )
            elif major_version and major_version >= 15:
                # Odoo 15+ uses account.move
                if move_exists:
                    raise UserError(
                        f'You are connecting to Odoo {major_version}{version_info}, which uses "account.move" instead of "account.invoice".\n\n'
                        'This migration module is designed specifically for migrating FROM Odoo 14 TO Odoo 19.\n\n'
                        'Please ensure you are connecting to an Odoo 14 instance:\n'
                        f'- Current URL: {self.config_id.odoo14_url}\n'
                        f'- Database: {self.config_id.odoo14_database}\n\n'
                        'If you need to migrate from Odoo 15+, a different migration approach would be required.'
                    )
                else:
                    raise UserError(
                        f'Model "account.move" not found in Odoo {major_version} instance{version_info}.\n\n'
                        'Please verify the account module is installed.'
                    )
            else:
                # Version unknown, try to detect by model existence
                if invoice_exists:
                    invoice_model = 'account.invoice'
                elif move_exists:
                    raise UserError(
                        f'Detected "account.move" model but version is unclear{version_info}.\n\n'
                        'This migration module is designed for Odoo 14. If you are connecting to Odoo 15+, '
                        'please use a different migration approach.'
                    )
                else:
                    raise UserError(
                        f'Could not determine invoice model{version_info}.\n\n'
                        'Please verify:\n'
                        '1. The account module is installed\n'
                        '2. Your user has proper access rights\n'
                        f'3. You are connecting to Odoo 14 (URL: {self.config_id.odoo14_url})'
                    )
            
            # Determine domain based on model
            if invoice_model == 'account.move':
                invoice_domain = [('move_type', '=', 'out_invoice')]
                purchase_domain = [('move_type', '=', 'in_invoice')]
            else:
                invoice_domain = [('type', '=', 'out_invoice')]
                purchase_domain = [('type', '=', 'in_invoice')]
            
            # Count invoices - handle case where model doesn't exist
            try:
                invoice_count = client.count(invoice_model, invoice_domain)
            except Exception as e:
                error_msg = str(e)
                if "doesn't exist" in error_msg.lower():
                    raise UserError(
                        f'Model "{invoice_model}" not found in Odoo 14. '
                        'Please ensure:\n'
                        '1. The account module is installed in Odoo 14\n'
                        '2. Your user has access rights to view invoices\n'
                        '3. You are connecting to an Odoo 14 instance (not Odoo 15+)'
                    )
                raise UserError(f'Error counting invoices: {error_msg}')
            
            # Count purchase invoices
            try:
                purchase_invoice_count = client.count(invoice_model, purchase_domain)
            except Exception as e:
                error_msg = str(e)
                if "doesn't exist" in error_msg.lower():
                    raise UserError(
                        'Model "account.invoice" not found in Odoo 14. '
                        'Please ensure the account module is installed and you have proper access rights.'
                    )
                raise UserError(f'Error counting purchase invoices: {error_msg}')
            
            # Write the values to update the form
            self.write({
                'invoice_count': invoice_count,
                'purchase_invoice_count': purchase_invoice_count
            })
            
            message = f"Found {invoice_count} customer invoices and {purchase_invoice_count} vendor bills in Odoo 14."
            
            # Reload the form to show updated values
            return {
                'type': 'ir.actions.act_window',
                'name': 'Start Migration',
                'res_model': 'odoo14.migration.wizard',
                'view_mode': 'form',
                'target': 'new',
                'res_id': self.id,
                'context': dict(self.env.context),
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error(f"Error checking data: {str(e)}")
            raise UserError(f'Error checking data: {str(e)}')

    def action_migrate(self):
        """Start the migration process"""
        self.ensure_one()
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        if not self.migrate_invoices and not self.migrate_purchase_invoices:
            raise UserError('Please select at least one document type to migrate.')
        
        if self.is_migrating:
            raise UserError('Migration is already in progress.')
        
        # Initialize migration
        self.write({
            'is_migrating': True,
            'migration_progress': 0.0,
            'invoices_migrated': 0,
            'purchase_invoices_migrated': 0,
            'errors_count': 0,
            'error_log': '',
            'migration_status': 'Starting migration...',
        })
        
        # Perform migration
        try:
            self._perform_migration()
        except Exception as e:
            _logger.error(f"Migration error: {str(e)}")
            self.write({
                'error_log': (self.error_log or '') + f"\nMigration failed: {str(e)}",
                'errors_count': self.errors_count + 1,
                'is_migrating': False,
                'migration_progress': 100.0,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Migration Results',
            'res_model': 'odoo14.migration.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

    def _perform_migration(self):
        """Perform the actual migration"""
        from ..models.odoo14_api_client import Odoo14APIClient
        
        client = Odoo14APIClient(
            url=self.config_id.odoo14_url,
            db=self.config_id.odoo14_database,
            username=self.config_id.odoo14_username,
            password=self.config_id.odoo14_password
        )
        
        if not client.authenticate():
            raise UserError('Failed to authenticate with Odoo 14.')
        
        total_records = 0
        if self.migrate_invoices:
            total_records += self.invoice_count
        if self.migrate_purchase_invoices:
            total_records += self.purchase_invoice_count
        
        if total_records == 0:
            self.migration_status = 'No records to migrate.'
            return
        
        migrated = 0
        
        # Get the invoice model to use
        invoice_model = client._get_invoice_model()
        
        # Migrate customer invoices
        if self.migrate_invoices:
            self.write({'migration_status': 'Migrating customer invoices...'})
            invoices = client.get_invoices(invoice_model=invoice_model)
            total_invoices = len(invoices)
            for idx, invoice in enumerate(invoices, 1):
                try:
                    self._migrate_invoice(client, invoice, 'out_invoice', invoice_model)
                    migrated += 1
                    self.write({
                        'invoices_migrated': self.invoices_migrated + 1,
                        'migration_progress': (migrated / total_records) * 100 if total_records > 0 else 0,
                        'migration_status': f'Migrating customer invoices... ({idx}/{total_invoices})',
                    })
                    # Commit progress every 10 records
                    if idx % 10 == 0:
                        self.env.cr.commit()
                except Exception as e:
                    _logger.error(f"Error migrating invoice {invoice.get('name', 'Unknown')}: {str(e)}")
                    self.write({
                        'error_log': (self.error_log or '') + f"\nInvoice {invoice.get('name', 'Unknown')}: {str(e)}",
                        'errors_count': self.errors_count + 1,
                    })
        
        # Migrate purchase invoices
        if self.migrate_purchase_invoices:
            self.write({'migration_status': 'Migrating vendor bills...'})
            purchase_invoices = client.get_purchase_invoices(invoice_model=invoice_model)
            total_purchase = len(purchase_invoices)
            for idx, invoice in enumerate(purchase_invoices, 1):
                try:
                    self._migrate_invoice(client, invoice, 'in_invoice', invoice_model)
                    migrated += 1
                    self.write({
                        'purchase_invoices_migrated': self.purchase_invoices_migrated + 1,
                        'migration_progress': (migrated / total_records) * 100 if total_records > 0 else 0,
                        'migration_status': f'Migrating vendor bills... ({idx}/{total_purchase})',
                    })
                    # Commit progress every 10 records
                    if idx % 10 == 0:
                        self.env.cr.commit()
                except Exception as e:
                    _logger.error(f"Error migrating purchase invoice {invoice.get('name', 'Unknown')}: {str(e)}")
                    self.write({
                        'error_log': (self.error_log or '') + f"\nPurchase Invoice {invoice.get('name', 'Unknown')}: {str(e)}",
                        'errors_count': self.errors_count + 1,
                    })
        
        self.write({
            'migration_status': f'Migration completed. Migrated {migrated} records with {self.errors_count} errors.',
            'migration_progress': 100.0,
            'is_migrating': False,
        })
        self.env.cr.commit()

    def _migrate_invoice(self, client, invoice_data, invoice_type, invoice_model='account.invoice'):
        """Migrate a single invoice"""
        # Extract partner_id (handle both list and integer formats)
        partner_id = invoice_data.get('partner_id')
        if isinstance(partner_id, list):
            partner_id = partner_id[0] if partner_id else None
        
        # Get or create partner
        partner = self._get_or_create_partner(client, partner_id)
        if not partner:
            raise UserError(f"Partner not found for invoice {invoice_data.get('name', 'Unknown')}")
        
        # Extract journal_id
        journal_id = invoice_data.get('journal_id')
        if isinstance(journal_id, list):
            journal_id = journal_id[0] if journal_id else None
        
        # Get journal
        journal = self._get_journal(journal_id)
        
        # Prepare invoice values - handle both account.invoice and account.move field names
        if invoice_model == 'account.move':
            # Odoo 15+ field names
            invoice_date = invoice_data.get('invoice_date')
            date_due = invoice_data.get('invoice_date_due')
            narration = invoice_data.get('narration', '')
        else:
            # Odoo 14 field names (account.invoice)
            invoice_date = invoice_data.get('invoice_date') or invoice_data.get('date_invoice')
            date_due = invoice_data.get('invoice_date_due') or invoice_data.get('date_due')
            narration = invoice_data.get('comment', '')
        
        invoice_vals = {
            'move_type': 'out_invoice' if invoice_type == 'out_invoice' else 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': invoice_date,
            'journal_id': journal.id if journal else False,
            'ref': invoice_data.get('name', ''),
            'narration': narration,
        }
        
        # Create invoice
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Set due date if available
        if date_due:
            invoice.invoice_date_due = date_due
        
        # Migrate invoice lines - handle both invoice_line_ids and line_ids
        invoice_line_ids = invoice_data.get('invoice_line_ids', []) or invoice_data.get('line_ids', [])
        for line_id in invoice_line_ids:
            try:
                lines = client.get_invoice_lines(line_id, invoice_model)
                if lines:
                    self._migrate_invoice_line(client, invoice, lines[0])
            except Exception as e:
                _logger.error(f"Error migrating invoice line {line_id}: {str(e)}")
        
        # Recompute totals
        invoice._recompute_dynamic_lines()
        invoice._recompute_payment_terms_lines()
        
        return invoice

    def _migrate_invoice_line(self, client, invoice, line_data):
        """Migrate a single invoice line"""
        # Extract product_id
        product_id = line_data.get('product_id')
        if isinstance(product_id, list):
            product_id = product_id[0] if product_id else None
        
        # Get or create product
        product = self._get_or_create_product(client, product_id)
        
        # Extract account_id
        account_id = line_data.get('account_id')
        if isinstance(account_id, list):
            account_id = account_id[0] if account_id else None
        
        # Get account
        account = self._get_account(account_id)
        
        # If no account, try to get default from product or journal
        if not account:
            if product and product.categ_id.property_account_income_categ_id:
                account = product.categ_id.property_account_income_categ_id
            elif invoice.journal_id.default_account_id:
                account = invoice.journal_id.default_account_id
        
        line_vals = {
            'move_id': invoice.id,
            'product_id': product.id if product else False,
            'name': line_data.get('name', '') or (product.name if product else ''),
            'quantity': line_data.get('quantity', 1.0),
            'price_unit': line_data.get('price_unit', 0.0),
            'discount': line_data.get('discount', 0.0),
            'account_id': account.id if account else False,
            'sequence': line_data.get('sequence', 10),
        }
        
        # Get taxes
        tax_ids = line_data.get('tax_ids', [])
        if tax_ids:
            # Handle list of IDs
            if isinstance(tax_ids[0], list):
                tax_ids = [tid[0] if isinstance(tid, list) else tid for tid in tax_ids]
            taxes = self._get_taxes(tax_ids)
            if taxes:
                line_vals['tax_ids'] = [(6, 0, taxes.ids)]
        
        return self.env['account.move.line'].create(line_vals)

    def _get_or_create_partner(self, client, partner_id):
        """Get or create partner from Odoo 14"""
        if not partner_id:
            return False
        
        # Check if partner already exists by external ID or name
        partner_data = client.get_partner(partner_id)
        if not partner_data:
            return False
        
        # Search for existing partner
        existing = self.env['res.partner'].search([
            '|',
            ('name', '=', partner_data.get('name')),
            ('vat', '=', partner_data.get('vat'))
        ], limit=1)
        
        if existing:
            return existing
        
        # Create new partner
        country = False
        country_id = partner_data.get('country_id')
        if country_id:
            country_id_val = country_id[0] if isinstance(country_id, list) else country_id
            if country_id_val:
                country = self.env['res.country'].browse(country_id_val)
                if not country.exists():
                    country = False
        
        state = False
        state_id = partner_data.get('state_id')
        if state_id:
            state_id_val = state_id[0] if isinstance(state_id, list) else state_id
            state_name = state_id[1] if isinstance(state_id, list) and len(state_id) > 1 else ''
            
            if state_id_val:
                state = self.env['res.country.state'].browse(state_id_val)
                if state.exists():
                    # Clean state name: remove (AE) and capitalize
                    if state_name:
                        cleaned_name = state_name.replace('(AE)', '').replace('(ae)', '').strip()
                        cleaned_name = ' '.join(word.capitalize() for word in cleaned_name.split())
                        # Update state name if it contains (AE)
                        if '(AE)' in state.name or '(ae)' in state.name:
                            state.write({'name': cleaned_name})
                else:
                    state = False
        
        partner_vals = {
            'name': partner_data.get('name', ''),
            'email': partner_data.get('email', ''),
            'phone': partner_data.get('phone', ''),
            'mobile': partner_data.get('mobile', ''),
            'street': partner_data.get('street', ''),
            'street2': partner_data.get('street2', ''),
            'city': partner_data.get('city', ''),
            'state_id': state.id if state else False,
            'zip': partner_data.get('zip', ''),
            'country_id': country.id if country else False,
            'vat': partner_data.get('vat', ''),
            'is_company': partner_data.get('is_company', False),
        }
        
        return self.env['res.partner'].create(partner_vals)

    def _get_or_create_product(self, client, product_id):
        """Get or create product from Odoo 14"""
        if not product_id:
            return False
        
        product_data = client.get_product(product_id)
        if not product_data:
            return False
        
        # Search for existing product
        existing = self.env['product.product'].search([
            '|',
            ('default_code', '=', product_data.get('default_code')),
            ('barcode', '=', product_data.get('barcode'))
        ], limit=1)
        
        if existing:
            return existing
        
        # Get category
        category = False
        categ_id = product_data.get('categ_id')
        if categ_id:
            categ_id_val = categ_id[0] if isinstance(categ_id, list) else categ_id
            if categ_id_val:
                category = self.env['product.category'].browse(categ_id_val)
                if not category.exists():
                    category = False
        
        # Get UOM
        uom = False
        uom_id = product_data.get('uom_id')
        if uom_id:
            uom_id_val = uom_id[0] if isinstance(uom_id, list) else uom_id
            if uom_id_val:
                uom = self.env['uom.uom'].browse(uom_id_val)
                if not uom.exists():
                    uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        
        product_vals = {
            'name': product_data.get('name', ''),
            'default_code': product_data.get('default_code', ''),
            'barcode': product_data.get('barcode', ''),
            'list_price': product_data.get('list_price', 0.0),
            'standard_price': product_data.get('standard_price', 0.0),
            'categ_id': category.id if category else False,
            'uom_id': uom.id if uom else False,
            'type': product_data.get('type', 'consu'),
            'sale_ok': product_data.get('sale_ok', True),
            'purchase_ok': product_data.get('purchase_ok', True),
        }
        
        return self.env['product.product'].create(product_vals)

    def _get_journal(self, journal_id):
        """Get journal by ID"""
        if not journal_id:
            return False
        journal = self.env['account.journal'].browse(journal_id)
        return journal if journal.exists() else False

    def _get_account(self, account_id):
        """Get account by ID"""
        if not account_id:
            return False
        account = self.env['account.account'].browse(account_id)
        return account if account.exists() else False

    def _get_taxes(self, tax_ids):
        """Get taxes by IDs"""
        if not tax_ids:
            return self.env['account.tax']
        taxes = self.env['account.tax'].browse(tax_ids)
        return taxes.filtered(lambda t: t.exists())

