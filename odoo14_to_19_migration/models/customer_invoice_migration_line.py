# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
from datetime import datetime
import time

_logger = logging.getLogger(__name__)


def _log_failed_invoice_migration(invoice_number, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_customer_invoice_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {invoice_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed invoice migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed migrations log: %s", str(e))


def _retry_on_serialization_error(func, max_retries=3, initial_delay=0.1):
    """
    Retry a function on PostgreSQL serialization errors with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_msg = str(e).lower()
            is_serialization_error = (
                'could not serialize' in error_msg or
                'concurrent update' in error_msg or
                'serialization failure' in error_msg or
                'deadlock detected' in error_msg
            )
            
            if is_serialization_error and attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)  # Exponential backoff
                _logger.warning("Serialization error (attempt %s/%s), retrying in %s seconds: %s", 
                             attempt + 1, max_retries, delay, str(e))
                time.sleep(delay)
                continue
            else:
                raise


def _search_account_safe(env, domain, company_id=None, limit=1, order=None):
    """
    Safely search for accounts, handling the case where 'deprecated' field might not exist.
    """
    account_env = env['account.account']
    if company_id:
        account_env = account_env.with_company(company_id)
    
    # Try with deprecated field first
    try:
        domain_with_deprecated = domain + [('deprecated', '=', False)]
        return account_env.search(domain_with_deprecated, limit=limit, order=order)
    except Exception as e:
        error_msg = str(e).lower()
        if 'deprecated' in error_msg or 'invalid field' in error_msg:
            # deprecated field doesn't exist, search without it
            return account_env.search(domain, limit=limit, order=order)
        else:
            raise


class CustomerInvoiceMigrationLine(models.Model):
    _name = 'customer.invoice.migration.line'
    _description = 'Customer Invoice Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    config_id = fields.Many2one('odoo14.migration.config', string='Migration Configuration', required=True)
    uploaded_invoice_number = fields.Char(string='Odoo 14 Invoice Number', required=True, index=True)
    odoo14_invoice_id = fields.Integer(string='Odoo 14 Invoice ID', help="ID of the invoice in Odoo 14")
    
    # Excel Fields
    company = fields.Char(string='Company (Excel)')
    invoice_bill_date = fields.Date(string='Invoice Date (Excel)')
    due_date = fields.Date(string='Due Date (Excel)')
    invoice_partner_name = fields.Char(string='Customer (Excel)')
    voucher_number = fields.Char(string='Voucher Number')
    quote_reference = fields.Char(string='Quote Reference')
    tax_id = fields.Char(string='Tax ID (Excel)')
    total_in_currency = fields.Float(string='Total in Currency (Excel)')
    number_of_items = fields.Integer(string='Number of items')
    amount_total = fields.Float(string='Amount Total')
    amount_tax = fields.Float(string='Amount Tax')
    currency_id = fields.Char(string='Currency')
    payment_state = fields.Char(string='Payment State')
    payment_status = fields.Char(string='Payment Status')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('pending_migration', 'Pending Migration'),
        ('queued', 'Queued'),
        ('migrating', 'Migrating'),
        ('migrated', 'Migrated'),
        ('error', 'Error'),
        ('skipped', 'Skipped')
    ], string='Status', default='pending', index=True, tracking=True)
    
    status_message = fields.Text(string='Status Message', tracking=True)
    error_message = fields.Text(string='Error Message')
    odoo19_invoice_id = fields.Many2one('account.move', string='Odoo 19 Invoice')
    odoo19_sale_order_id = fields.Many2one('sale.order', string='Odoo 19 Sale Order')
    in_system_invoice_number = fields.Char(string='In-System Invoice Number')
    migration_date = fields.Datetime(string='Migration Date')
    
    # Item count tracking
    total_items_odoo14 = fields.Integer(string='Total Items (O14)', help="Total lines found in Odoo 14")
    total_items_odoo19 = fields.Integer(string='Total Items (O19)', help="Total lines created in Odoo 19")
    excel_status = fields.Char(string='Excel Status')

    def check_status(self, invoice_number=None, config_id=None):
        """Check status of a customer invoice number against Odoo 14 and Odoo 19"""
        self.ensure_one()
        if not invoice_number:
            invoice_number = self.uploaded_invoice_number
        if not config_id:
            config_id = self.config_id
        if not config_id:
            return {'status': 'not_found', 'message': 'No configuration'}
        
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=config_id.odoo14_url,
                db=config_id.odoo14_database,
                username=config_id.odoo14_username,
                password=config_id.odoo14_password
            )
            
            if not client.authenticate():
                return {'status': 'error', 'message': 'Failed to authenticate with Odoo 14'}
            
            # Check in Odoo 19 first (already migrated?)
            existing_19 = self.env['account.move'].search([
                ('name', '=', invoice_number),
                ('move_type', '=', 'out_invoice')
            ], limit=1)
            
            if existing_19:
                return {
                    'status': 'already_migrated',
                    'message': 'Already exists in Odoo 19',
                    'odoo19_id': existing_19.id,
                    'odoo19_name': existing_19.name
                }
            
            # Check in Odoo 14
            invoices = []
            try:
                # Search by name first
                invoices = client.search_read(
                    'account.move',
                    [('name', '=', invoice_number), ('move_type', '=', 'out_invoice')],
                    ['id', 'name'],
                    limit=1
                )
                if not invoices and invoice_number:
                     # Fallback to ref
                     invoices = client.search_read(
                        'account.move',
                        [('ref', '=', invoice_number), ('move_type', '=', 'out_invoice')],
                        ['id', 'name'],
                        limit=1
                    )
            except Exception as e:
                _logger.debug("Error checking Odoo 14: %s", str(e))
            
            if invoices:
                return {
                    'status': 'pending_migration',
                    'message': 'Found in Odoo 14, ready to migrate',
                    'odoo14_id': invoices[0]['id'],
                    'odoo14_name': invoices[0]['name']
                }
            else:
                return {
                    'status': 'not_found',
                    'message': 'Not found in Odoo 14'
                }
                
        except Exception as e:
            _logger.error("Error checking invoice status: %s", str(e))
            return {'status': 'error', 'message': str(e)}

    def action_check_status(self):
        """Button action to refresh status"""
        for record in self:
            result = record.check_status()
            record.write({
                'status': result.get('status', 'not_found'),
                'status_message': result.get('message', ''),
                'in_system_invoice_number': result.get('odoo14_name') or result.get('odoo19_name') or '',
                'odoo14_invoice_id': result.get('odoo14_id', 0),
                'odoo19_invoice_id': result.get('odoo19_id', False),
            })

    @api.model
    def action_open_upload_wizard(self):
        """Open the Excel upload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'customer.invoice.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': 'Upload Excel',
        }

    def action_bulk_migrate(self):
        """Bulk migrate selected invoices: Mark as QUEUED for continuous processor"""
        pending = self.filtered(lambda r: r.status in ('pending_migration', 'error'))
        
        if pending:
            pending.write({
                'status': 'queued', 
                'status_message': 'Queued for migration',
                'error_message': False
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Invoices Queued',
                'message': f'{len(pending)} invoices marked as Queued. Run the continuous migration script to process them.',
                'type': 'success',
            }
        }
    
    def action_start_queued_migration(self):
         # Stub for now
         return self.action_bulk_migrate()

    def action_migrate(self):
        self.ensure_one()
        try:
            # 1. Configuration & Authentication
            if not self.config_id:
                raise UserError('Migration configuration is missing.')
            
            from ..models.odoo14_api_client import Odoo14APIClient
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Authentication failed with Odoo 14.')
            
            _logger.info("=" * 80)
            _logger.info("🚀 STARTING CUSTOMER INVOICE MIGRATION: %s", self.uploaded_invoice_number)
            _logger.info("=" * 80)
            
            # 2. Fetch Invoice Data from Odoo 14
            odoo14_id = self.odoo14_invoice_id
            if not odoo14_id:
                # Try to search by name
                invoice_search = client.search_read(
                    'account.move',
                    [('name', '=', self.uploaded_invoice_number), ('move_type', '=', 'out_invoice')],
                    ['id'], limit=1
                )
                if invoice_search:
                    odoo14_id = invoice_search[0]['id']
                    self.odoo14_invoice_id = odoo14_id
            
            if not odoo14_id:
                # Last resort: search by reference if provided
                if self.uploaded_invoice_number:
                     invoice_search = client.search_read(
                        'account.move',
                        [('ref', '=', self.uploaded_invoice_number), ('move_type', '=', 'out_invoice')],
                        ['id'], limit=1
                    )
                     if invoice_search:
                        odoo14_id = invoice_search[0]['id']
            
            if not odoo14_id:
                raise UserError(f"Invoice {self.uploaded_invoice_number} not found in Odoo 14")
            
            _logger.info("✅ Found Odoo 14 Invoice ID: %s", odoo14_id)
            
            # Fetch full invoice data
            # Use 'out_invoice' specific fields if needed
            invoice_data_list = client.search_read(
                'account.move',
                [('id', '=', odoo14_id)],
                ['name', 'date', 'invoice_date', 'invoice_date_due', 'currency_id', 'company_id', 
                 'partner_id', 'journal_id', 'ref', 'narration', 'state', 'payment_state', 
                 'amount_total', 'amount_untaxed', 'invoice_user_id', 'team_id',
                 'invoice_origin', 'fiscal_position_id', 'invoice_payment_term_id',
                 'create_date', 'write_date', 'create_uid', 'write_uid',
                 'location', 'site_name', 'create_do', 'bank_details', 'file_to_upload', 'filename'],
                limit=1
            )
            
            if not invoice_data_list:
                raise UserError(f"Could not read data for invoice ID {odoo14_id}")
            
            invoice_data = invoice_data_list[0]
            
            # Prepare Odoo 19 Invoice Values
            invoice_vals = {
                'move_type': 'out_invoice',
                'name': invoice_data.get('name') or self.uploaded_invoice_number,
                'invoice_date': invoice_data.get('invoice_date') or self.invoice_bill_date or fields.Date.today(),
                'date': invoice_data.get('date') or fields.Date.today(),
                'invoice_date_due': invoice_data.get('invoice_date_due') or self.due_date,
                'ref': invoice_data.get('ref'),
                'narration': invoice_data.get('narration'),
                'invoice_origin': invoice_data.get('invoice_origin'),
            }
            
            # Map Custom Fields
            for custom_field in ['location', 'site_name', 'create_do', 'bank_details', 'file_to_upload', 'filename']:
                if invoice_data.get(custom_field):
                    invoice_vals[custom_field] = invoice_data[custom_field]

            # 3. Map Company (Robust Logic)
            company = False
            source = "None"
            
            # Priority 1: Excel Company Name
            if self.company:
                company = self.env['res.company'].search([('name', 'ilike', self.company)], limit=1)
                if company:
                    source = f"Excel Mapping ('{self.company}')"

            # Priority 2: Odoo 14 Company ID
            if not company and invoice_data.get('company_id'):
                c_id = invoice_data['company_id'][0] if isinstance(invoice_data['company_id'], list) else invoice_data['company_id']
                company = self.env['res.company'].search([('id', '=', c_id)], limit=1)
                if company:
                    source = f"Odoo 14 ID ({c_id})"
            
            # Fallback: Current Company
            if not company:
                company = self.env.company
                source = f"Default User Company ({company.name})"
            
            invoice_vals['company_id'] = company.id
            _logger.info("✅ Mapped Company: %s (Source: %s)", company.name, source)
            
            # 4. Map Partner (Customer)
            partner_id_val = invoice_data.get('partner_id')
            partner = False
            if partner_id_val:
                p_id = partner_id_val[0] if isinstance(partner_id_val, list) else partner_id_val
                # Try by ID first
                partner = self.env['res.partner'].search([('id', '=', p_id)], limit=1)
                if not partner:
                    # Try fetch name
                    try:
                        p_data = client.search_read('res.partner', [('id', '=', p_id)], ['name', 'email', 'phone', 'is_company', 'vat'], limit=1)
                        if p_data:
                            # Search by Name
                            partner = self.env['res.partner'].search([('name', '=', p_data[0]['name'])], limit=1)
                            # If not found, create
                            if not partner:
                                _logger.info("📦 Creating new partner: %s", p_data[0]['name'])
                                partner = self.env['res.partner'].create({
                                    'name': p_data[0]['name'],
                                    'email': p_data[0]['email'],
                                    'phone': p_data[0]['phone'],
                                    'is_company': p_data[0]['is_company'],
                                    'vat': p_data[0].get('vat')
                                })
                    except Exception as e:
                        _logger.warning("Partner fetch error: %s", str(e))
            
            if partner:
                invoice_vals['partner_id'] = partner.id
            else:
                raise UserError("Partner is required for Customer Invoice")

            # 5. Map Currency (Always AED preferred if local, or map safely)
            # Actually, per file requirement, customer invoice usually is AED, but let's follow source if possible or company default
            # Previous logic hardcoded AED. Let's try to be smart.
            aed_currency = self.env['res.currency'].search([('name', '=', 'AED')], limit=1)
            invoice_vals['currency_id'] = aed_currency.id if aed_currency else company.currency_id.id
            
            # 6. Map Journal (Sales Journal) - CRITICAL: Company Check
            journal = False
            if invoice_data.get('journal_id'):
                j_id = invoice_data['journal_id'][0] if isinstance(invoice_data['journal_id'], list) else invoice_data['journal_id']
                journal = self.env['account.journal'].search([('id', '=', j_id), ('company_id', '=', company.id)], limit=1)
            
            if not journal:
                 journal = self.env['account.journal'].search([
                     ('type', '=', 'sale'),
                     ('company_id', '=', company.id)
                 ], limit=1)
            
            if not journal:
                raise UserError(f"No Sales Journal found for company {company.name}")
            
            invoice_vals['journal_id'] = journal.id
            
            # 7. Create Invoice Header
            # We create in draft first
            try:
                invoice = self.env['account.move'].with_company(company.id).create(invoice_vals)
                _logger.info("✅ Created Invoice Header: %s (ID: %s)", invoice.name, invoice.id)
            except Exception as e:
                raise UserError(f"Failed to create invoice header: {str(e)}")

            # 8. Migrate Lines (Robust Loop)
            # Fetch lines directly
            _logger.info("🔄 Fetching invoice lines from Odoo 14...")
            all_lines = client.search_read(
                'account.move.line',
                [('move_id', '=', odoo14_id), ('display_type', '=', False)],
                ['id', 'product_id', 'name', 'quantity', 'price_unit', 'discount', 'tax_ids', 
                 'account_id', 'sequence', 'display_type', 'tax_line_id'],
                limit=200
            )

            if not all_lines:
                 _logger.warning("⚠️ No lines found for invoice %s", odoo14_id)
            
            # Deduplicate and Filter
            seen_combinations = {}
            lines_to_process = []
            
            for line in all_lines:
                # Skip tax lines only (keep sections/notes if needed, or skip them if they are purely headers)
                if line.get('tax_line_id') or line.get('display_type'):
                    continue
                
                # Product ID (might be False for label-only lines)
                pid = line.get('product_id')
                pid_val = pid[0] if isinstance(pid, list) else pid
                
                # DEDUPLICATION REMOVED: Customer invoices often have multiple lines for same product
                
                lines_to_process.append(line)

            
            # Update Item Count
            self.total_items_odoo14 = len(lines_to_process)
            
            processed_count = 0
            
            for idx, line_data in enumerate(lines_to_process):
                _logger.info("Processing Line %s/%s", idx+1, len(lines_to_process))
                
                try:
                    line_vals = {
                        'move_id': invoice.id,
                        'company_id': company.id,
                        'name': line_data.get('name', 'Line'),
                        'quantity': line_data.get('quantity', 1.0),
                        'price_unit': line_data.get('price_unit', 0.0),
                        'discount': line_data.get('discount', 0.0),
                        'sequence': line_data.get('sequence', 10),
                    }
                    
                    # A. Map Product (Robust)
                    product_id_raw = line_data.get('product_id')
                    product = False
                    if product_id_raw:
                        p_id = product_id_raw[0] if isinstance(product_id_raw, list) else product_id_raw
                        # 1. ID Match
                        product = self.env['product.product'].search([('id', '=', p_id)], limit=1)
                        # 2. Details Match
                        if not product:
                            try:
                                prod_details = client.search_read('product.product', [('id', '=', p_id)], ['name', 'default_code', 'barcode', 'type'], limit=1)
                                if prod_details:
                                    pd = prod_details[0]
                                    if pd.get('default_code'):
                                         product = self.env['product.product'].search([('default_code', '=', pd['default_code'])], limit=1)
                                    if not product and pd.get('name'):
                                         product = self.env['product.product'].search([('name', '=', pd['name'])], limit=1)
                                    
                                    # Create if missing
                                    if not product:
                                        _logger.info("📦 Creating Product: %s", pd.get('name'))
                                        product = self.env['product.product'].create({
                                            'name': pd.get('name', 'Migrated Product'),
                                            'default_code': pd.get('default_code'),
                                            'type': 'consu', # Service/Consumable safer for migration
                                            'sale_ok': True
                                        })
                            except Exception as pe:
                                _logger.warning("Product Map Error: %s", str(pe))
                            
                            # CRITICAL: If Odoo 14 has "Migration Fallback Product" (from previous bad migration), ignore it!
                            if product and ('Fallback' in product.name or 'MIG_W_FALLBACK' in product.default_code):
                                _logger.info("Ignoring Odoo 14 Fallback Product: %s", product.name)
                                product = False
                    
                    # SPECIFIC FIX: Down Payment Logic
                    # If product mapping failed, checks if it's a Down Payment line
                    if not product and 'Down payment' in line_data.get('name', ''):
                        dp_product = self.env['product.product'].search([('name', 'ilike', 'Down Payment')], limit=1)
                        if not dp_product:
                             dp_product = self.env['product.product'].create({
                                 'name': 'Down Payment',
                                 'type': 'service',
                                 'default_code': 'DOWN_PAYMENT'
                             })
                        product = dp_product
                        _logger.info("Fixed Down Payment product mapping for line '%s'", line_data.get('name'))
                    
                    if product:
                        line_vals['product_id'] = product.id
                    else:
                        # Fallback for product (if missing in O14 or mapping failed)
                        # User Request: If product not found (fallback scenario), REMOVE the line.
                        # Skipping the line allows the invoice total to recalculate without this line.
                        
                        _logger.info("Skipping line '%s' (O14 Product ID: %s) as product could not be mapped.", line_data.get('name'), product_id_raw)
                        continue
                        
                        # Preserve original name if it was a label-only line
                        # if not product_id_raw:
                        #      line_vals['name'] = line_data.get('name', 'Line description')

                    # B. Map Account (401100 Enforced)
                    # 1. Try 401100 in Company
                    account = _search_account_safe(self.env, [('code', '=', '401100')], company_id=company.id, limit=1)
                    
                    # 2. Fallback: Default Income
                    if not account:
                        account = _search_account_safe(self.env, [('internal_group', '=', 'income')], company_id=company.id, limit=1)
                    
                    if not account:
                        raise UserError(f"No Income Account (401100 or other) found for company {company.name}")
                    
                    line_vals['account_id'] = account.id

                    # C. Map Tax (Company Default Sale Tax)
                    # Priority: Company Default > Product DefaultO14 > None
                    taxes = self.env['account.tax']
                    if company.account_sale_tax_id:
                        taxes = company.account_sale_tax_id
                    
                    if not taxes and line_data.get('tax_ids'):
                         # Try mapping O14 taxes if no company default (optional, can skip for consistency)
                         pass

                    if taxes:
                        # Ensure tax company matches
                        taxes = taxes.filtered(lambda t: t.company_id.id == company.id)
                        if taxes:
                            line_vals['tax_ids'] = [(6, 0, taxes.ids)]

                    # Create Line
                    self.env['account.move.line'].with_company(company.id).create(line_vals)
                    self.env.cr.commit()
                    processed_count += 1
                
                except Exception as le:
                    _logger.error("Line Migration Failed: %s", str(le))
                    # Continue to next line? Yes, consistent with vendor bill logic
            
            self.total_items_odoo19 = processed_count
            
            # 9. Post Logic
            should_post = False
            if invoice_data.get('state') == 'posted':
                should_post = True
            
            if should_post and invoice.state == 'draft':
                 try:
                    # Validate lines exist
                    if not invoice.invoice_line_ids:
                        _logger.warning("Invoice has no lines, cannot post!")
                    else:
                        invoice.action_post()
                        _logger.info("✅ Posted Invoice")
                 except Exception as pe:
                     _logger.warning("Could not post invoice: %s", str(pe))

            # Success
            self.write({
                'status': 'migrated',
                'status_message': 'Successfully migrated',
                'odoo19_invoice_id': invoice.id,
                'in_system_invoice_number': invoice.name,
                'migration_date': fields.Datetime.now(),
                'error_message': False
            })
            self.env.cr.commit()
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'customer.invoice.migration.line',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'current',
            }

        except Exception as e:
            self.env.cr.rollback()
            error_msg = str(e)
            self.write({
                'status': 'error',
                'error_message': error_msg,
                'status_message': 'Error: ' + error_msg
            })
            self.env.cr.commit()
            _log_failed_invoice_migration(self.uploaded_invoice_number, error_msg)
            raise UserError(str(e))
