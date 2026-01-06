# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


def _log_failed_invoice_migration(invoice_number, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_invoice_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {invoice_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed invoice migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed migrations log: %s", str(e))


def _check_queue_job_available(env):
    """Comprehensive check if queue_job is available and working"""
    try:
        module = env['ir.module.module'].search([
            ('name', '=', 'queue_job'),
            ('state', '=', 'installed')
        ], limit=1)
        if not module:
            return False, 'Module not installed in database'
    except Exception as e:
        return False, f'Error checking database: {str(e)}'
    
    try:
        if 'queue.job' not in env.registry:
            return False, 'Module not loaded in registry (restart needed)'
    except Exception as e:
        return False, f'Error checking registry: {str(e)}'
    
    try:
        from odoo.addons.queue_job.job import Job
    except ImportError as e:
        return False, f'Cannot import Job class: {str(e)}'
    
    try:
        test_model = env['res.users']
        if not hasattr(test_model, 'with_delay'):
            return False, 'with_delay method not available (restart needed)'
    except Exception as e:
        return False, f'Error checking with_delay: {str(e)}'
    
    return True, 'OK'


class CustomerInvoiceMigrationLine(models.Model):
    """Model to store uploaded invoice numbers and track migration status"""
    _name = 'customer.invoice.migration.line'
    _description = 'Customer Invoice Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    uploaded_invoice_number = fields.Char(
        string='Number',
        required=True,
        index=True,
        help='Invoice number from Excel upload'
    )
    
    in_system_invoice_number = fields.Char(
        string='In-System Invoice Number',
        readonly=True,
        help='Actual invoice number found in Odoo 14 or Odoo 19'
    )
    
    # Additional fields from Excel
    voucher_number = fields.Char(
        string='Voucher Number',
        help='Voucher number from Excel'
    )
    
    invoice_partner_name = fields.Char(
        string='Invoice Partner Name',
        help='Customer/Partner name from Excel'
    )
    
    invoice_bill_date = fields.Date(
        string='Invoice/Bill Date',
        help='Invoice date from Excel'
    )
    
    due_date = fields.Date(
        string='Due Date',
        help='Due date from Excel'
    )
    
    excel_status = fields.Char(
        string='Status (Excel)',
        help='Status from Excel file'
    )
    
    payment_status = fields.Char(
        string='Payment Status (Excel)',
        help='Payment status from Excel file'
    )
    
    company = fields.Char(
        string='Company',
        help='Company/Branch name from Excel'
    )
    
    quote_reference = fields.Char(
        string='Quote Reference',
        help='Quote reference from Excel'
    )
    
    status = fields.Selection([
        ('already_migrated', 'Already Migrated'),
        ('pending_migration', 'Pending Migration'),
        ('queued', 'Queued'),
        ('not_found', 'Not Found'),
        ('migrating', 'Migrating'),
        ('migrated', 'Migrated'),
        ('error', 'Error'),
    ], string='Status', default='pending_migration', readonly=True, index=True)
    
    status_message = fields.Text(string='Status Message', readonly=True)
    
    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=False,
        help='Optional: Odoo 14 connection configuration for status checking and migration'
    )
    
    odoo14_invoice_id = fields.Integer(
        string='Odoo 14 Invoice ID',
        readonly=True,
        help='ID of invoice in Odoo 14 if found'
    )
    
    odoo19_invoice_id = fields.Many2one(
        'account.move',
        string='Odoo 19 Invoice',
        readonly=True,
        domain=[('move_type', '=', 'out_invoice')],
        help='Migrated invoice in Odoo 19'
    )
    
    odoo19_sale_order_id = fields.Many2one(
        'sale.order',
        string='Linked Sale Order',
        readonly=True,
        help='Linked sale order in Odoo 19'
    )
    
    migration_date = fields.Datetime(string='Migration Date', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    def check_status(self, invoice_number=None, config_id=None):
        """Check status of an invoice number against Odoo 14 and Odoo 19"""
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
                invoices = client.search_read(
                    'account.move',
                    [('name', '=', invoice_number), ('move_type', '=', 'out_invoice')],
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
        """Bulk migrate selected invoices sequentially using Queue Jobs"""
        try:
            pending = self.filtered(lambda l: l.status == 'pending_migration')
            if not pending:
                raise UserError('No invoices with "Pending Migration" status selected')
            
            is_available, reason = _check_queue_job_available(self.env)
            if not is_available:
                raise UserError(
                    f'Queue Job module is not properly available.\n\n'
                    f'Reason: {reason}\n\n'
                    f'Please:\n'
                    f'1. Install "queue_job" module from Apps menu (if not installed)\n'
                    f'2. Upgrade "odoo14_to_19_migration" module (Apps → Search → Upgrade)\n'
                    f'3. Fully restart Odoo server\n'
                    f'4. Try again'
                )
            
            pending_ids = pending.ids
            if not pending_ids:
                raise UserError('No invoices with "Pending Migration" status selected')
            
            fresh_pending = self.env['customer.invoice.migration.line'].browse(pending_ids)
            for record in fresh_pending:
                record.write({
                    'status': 'queued',
                    'status_message': 'Queued for migration - waiting to be processed',
                    'error_message': False,
                })
            self.env.cr.commit()
            _logger.info("✅ Marked %s invoices as 'queued' (ready for processing)", len(fresh_pending))
        
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Invoices Queued',
                    'message': f'{len(pending_ids)} invoices have been queued. Use "Start Queued Migration" to start the migration process.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error in action_bulk_migrate: %s", str(e), exc_info=True)
            raise UserError(f'Error queuing invoices: {str(e)}')
    
    def action_start_queued_migration(self):
        """Start processing queued invoices - enqueue the first job to start sequential migration"""
        queued = self.filtered(lambda l: l.status == 'queued')
        if not queued:
            raise UserError('No invoices with "Queued" status selected')
        
        is_available, reason = _check_queue_job_available(self.env)
        if not is_available:
            raise UserError(
                f'Queue Job module is not properly available.\n\n'
                f'Reason: {reason}\n\n'
                f'Please:\n'
                f'1. Install "queue_job" module from Apps menu (if not installed)\n'
                f'2. Upgrade "odoo14_to_19_migration" module (Apps → Search → Upgrade)\n'
                f'3. Fully restart Odoo server\n'
                f'4. Try again'
            )
        
        queued_ids = queued.ids
        if not queued_ids:
            raise UserError('No invoices with "Queued" status selected')
        
        try:
            first_record = self.browse(queued_ids[0])
            if not first_record.exists():
                raise UserError(f'Record {queued_ids[0]} no longer exists')
            
            job = first_record.with_delay()._migrate_sequential(queued_ids, 0)
            
            _logger.info("✅ Started sequential migration for %s queued invoices (job UUID: %s)", 
                        len(queued_ids), getattr(job, 'uuid', 'N/A'))
            
            queued.write({
                'status_message': 'Migration process started - job enqueued',
            })
            self.env.cr.commit()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Migration Started',
                    'message': f'Started processing {len(queued_ids)} queued invoices. Migration will continue sequentially.',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except AttributeError as e:
            error_msg = str(e)
            _logger.error("Queue Job AttributeError: %s", error_msg, exc_info=True)
            raise UserError(
                f'Queue Job error: {error_msg}\n\n'
                f'This usually means queue_job module is not properly loaded.\n'
                f'Please:\n'
                f'1. Ensure queue_job module is installed and activated\n'
                f'2. Upgrade "odoo14_to_19_migration" module\n'
                f'3. Fully restart Odoo server\n'
                f'4. Check Odoo logs for details'
            )
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            _logger.error("Error starting queued migration (%s): %s", error_type, error_msg, exc_info=True)
            raise UserError(
                f'Error starting migration: {error_msg}\n\n'
                f'Error type: {error_type}\n'
                f'Please check Odoo logs for more details.'
            )
    
    def action_migrate(self):
        """Migrate this invoice from Odoo 14 to Odoo 19"""
        self.ensure_one()
        
        if self.status not in ('pending_migration', 'queued'):
            raise UserError('Can only migrate invoices with "Pending Migration" or "Queued" status')
        
        if not self.config_id:
            raise UserError('Migration configuration is required')
        
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
            
            # Get initial invoice data from Odoo 14
            safe_initial_fields = ['id', 'name']
            invoices = []
            
            try:
                invoices = client.search_read(
                    'account.move',
                    [('name', '=', self.uploaded_invoice_number), ('move_type', '=', 'out_invoice')],
                    safe_initial_fields,
                    limit=1
                )
            except Exception as e:
                _logger.debug("Error fetching invoice: %s", str(e))
            
            if not invoices:
                self.write({
                    'status': 'not_found',
                    'status_message': 'Invoice not found in Odoo 14',
                })
                return
            
            invoice_data = invoices[0]
            
            # Check if invoice already exists in Odoo 19 BEFORE migrating
            existing_invoice = self.env['account.move'].search([
                ('name', '=', self.uploaded_invoice_number),
                ('move_type', '=', 'out_invoice')
            ], limit=1)
            
            if existing_invoice:
                _logger.info("Invoice %s already exists in Odoo 19 (ID: %s), marking as migrated", 
                           self.uploaded_invoice_number, existing_invoice.id)
                self.write({
                    'status': 'migrated',
                    'status_message': 'Already migrated (existed in system)',
                    'odoo19_invoice_id': existing_invoice.id,
                    'in_system_invoice_number': existing_invoice.name,
                    'migration_date': fields.Datetime.now(),
                    'error_message': False,
                })
                self.env.cr.commit()
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'customer.invoice.migration.line',
                    'view_mode': 'list,form',
                    'target': 'current',
                }
            
            # Update status to migrating
            self.write({
                'status': 'migrating',
                'status_message': 'Migration in progress...',
            })
            self.env.cr.commit()
            
            # Get fields to fetch - dynamically check which fields exist
            excluded_fields = ['display_name', 'name_get', 'name_search']
            
            # Standard fields for account.move (customer invoice)
            fields_to_fetch = [
                'id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due', 'state', 'payment_state',
                'amount_total', 'amount_untaxed', 'amount_tax', 'currency_id', 'journal_id', 'ref', 'narration',
                'invoice_origin', 'invoice_payment_term_id', 'fiscal_position_id', 'user_id',
                'invoice_line_ids', 'line_ids',
                'create_date', 'write_date', 'write_uid', 'create_uid',
                # Custom fields from metro_erp
                'location', 'site_name', 'create_do', 'picking_ids', 'is_wo_header', 'bank_details',
                'file_to_upload', 'filename', 'is_with_stamp', 'voucher_no', 'in_note', 'quote_reference',
            ]
            
            # Try to get all fields dynamically
            try:
                all_fields = client.fields_get('account.move')
                if all_fields:
                    dynamic_fields = []
                    for f, field_info in all_fields.items():
                        if f in excluded_fields or f in fields_to_fetch:
                            continue
                        field_type = field_info.get('type', '')
                        field_store = field_info.get('store', True)
                        if not field_store:
                            continue
                        if field_type in ('one2many', 'many2many') and f not in ('invoice_line_ids', 'line_ids', 'picking_ids'):
                            continue
                        if field_type in ('char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime', 'many2one', 'selection', 'binary'):
                            dynamic_fields.append(f)
                    fields_to_fetch = list(set(fields_to_fetch + dynamic_fields))
            except Exception as e:
                _logger.warning("Could not get all fields: %s", str(e))
            
            minimal_safe_fields = [
                'id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due', 'state', 'payment_state',
                'amount_total', 'currency_id', 'journal_id', 'invoice_line_ids',
                'create_date', 'write_date'
            ]
            
            try:
                full_invoice = client.search_read(
                    'account.move',
                    [('id', '=', invoice_data['id'])],
                    fields_to_fetch,
                    limit=1
                )
            except Exception as e:
                _logger.warning("Error fetching invoice with expanded fields: %s. Using minimal safe fields.", str(e))
                full_invoice = client.search_read(
                    'account.move',
                    [('id', '=', invoice_data['id'])],
                    minimal_safe_fields,
                    limit=1
                )
            
            if not full_invoice:
                raise UserError('Could not fetch full invoice data')
            
            invoice_data = full_invoice[0]
            
            # Prepare invoice values for Odoo 19
            invoice_vals = {
                'move_type': 'out_invoice',  # Customer invoice
            }
            
            # Map name (invoice number) - REQUIRED
            if invoice_data.get('name'):
                invoice_vals['name'] = invoice_data['name']
            else:
                invoice_vals['name'] = self.uploaded_invoice_number
            
            # Map partner_id (required field)
            if invoice_data.get('partner_id'):
                partner_id = invoice_data['partner_id']
                if isinstance(partner_id, (list, tuple)) and len(partner_id) > 0:
                    partner_id = partner_id[0]
                partner = self.env['res.partner'].search([('id', '=', partner_id)], limit=1)
                if not partner:
                    # Try to get partner from Odoo 14
                    try:
                        partner_data = client.search_read(
                            'res.partner',
                            [('id', '=', partner_id)],
                            ['name', 'email', 'phone', 'is_company'],
                            limit=1
                        )
                        if partner_data:
                            partner = self.env['res.partner'].create({
                                'name': partner_data[0].get('name', 'Unknown'),
                                'email': partner_data[0].get('email', False),
                                'phone': partner_data[0].get('phone', False),
                                'is_company': partner_data[0].get('is_company', True),
                            })
                    except:
                        pass
                if partner:
                    invoice_vals['partner_id'] = partner.id
                else:
                    raise UserError('Could not find or create partner for invoice')
            else:
                raise UserError('Partner is required for invoice')
            
            # Map company_id - Priority: Excel company name > Odoo 14 branch_id (via mapping) > Odoo 14 company_id
            company = False
            
            # Priority 1: Try to find company from Excel company field
            if self.company:
                company = self.env['res.company'].search([
                    ('name', 'ilike', self.company)
                ], limit=1)
                if company:
                    _logger.info("✅ Found company '%s' (ID: %s) from Excel field for invoice %s", 
                               company.name, company.id, self.uploaded_invoice_number)
            
            # Priority 2: Try Odoo 14 branch_id (map to Odoo 19 company via branch_company_mapping)
            if not company:
                branch_id = invoice_data.get('branch_id')
                branch_name = None
                
                if branch_id:
                    if isinstance(branch_id, (list, tuple)) and len(branch_id) > 0:
                        # Many2one format: [id, name]
                        if len(branch_id) > 1:
                            branch_id_value = branch_id[0]
                            branch_name = branch_id[1]  # Extract branch name
                        else:
                            branch_id_value = branch_id[0]
                        branch_id = branch_id_value
                    
                    # Fetch branch name from Odoo 14 if not already extracted
                    if not branch_name and branch_id:
                        try:
                            # Try common branch models
                            for model_name in ['res.branch', 'account.branch', 'branch.branch', 'res.company.branch']:
                                try:
                                    branch_data_fetch = client.search_read(
                                        model_name,
                                        [('id', '=', branch_id)],
                                        ['name'],
                                        limit=1
                                    )
                                    if branch_data_fetch:
                                        branch_name = branch_data_fetch[0].get('name')
                                        break
                                except:
                                    continue
                        except Exception:
                            pass
                    
                    # Use branch_company_mapping
                    try:
                        mapping_model = self.env['odoo14.branch.company.mapping']
                        if mapping_model:
                            # Try mapping by branch_id first
                            company = mapping_model.get_company_for_branch(odoo14_branch_id=branch_id, odoo14_branch_name=None)
                            if company:
                                _logger.info("✅ Found company '%s' from Odoo 14 branch_id %s via mapping", company.name, branch_id)
                            elif branch_name:
                                # Try by branch_name
                                company = mapping_model.get_company_for_branch(odoo14_branch_id=None, odoo14_branch_name=branch_name)
                                if company:
                                    _logger.info("✅ Found company '%s' from Odoo 14 branch_name '%s' via mapping", company.name, branch_name)
                    except Exception:
                        pass
                    
                    # Direct name match fallback
                    if not company and branch_name:
                        company = self.env['res.company'].search([('name', '=', branch_name)], limit=1)
                        if not company:
                            company = self.env['res.company'].search([('name', 'ilike', branch_name)], limit=1)
                        if company:
                            _logger.info("✅ Found company '%s' by direct name match with branch '%s'", company.name, branch_name)
            
            # Priority 3: Try Odoo 14 company_id
            if not company:
                company_id = invoice_data.get('company_id')
                if company_id:
                    if isinstance(company_id, (list, tuple)) and len(company_id) > 0:
                        company_id = company_id[0]
                    # Try by ID
                    company = self.env['res.company'].search([('id', '=', company_id)], limit=1)
                    if not company:
                        # Try fetch name from Odoo 14 and match by name
                        try:
                            c_data = client.search_read('res.company', [('id', '=', company_id)], ['name'], limit=1)
                            if c_data:
                                company = self.env['res.company'].search([('name', 'ilike', c_data[0]['name'])], limit=1)
                        except:
                            pass
                    if company:
                        _logger.info("✅ Found company '%s' (ID: %s) from Odoo 14 company_id", company.name, company.id)
            
            # Fallback
            if not company:
                company = self.env.company
                _logger.warning("⚠️ Company not found, using default: %s", company.name)
            
            invoice_vals['company_id'] = company.id
            
            # Map invoice_date
            if invoice_data.get('invoice_date'):
                invoice_vals['invoice_date'] = invoice_data['invoice_date']
            elif self.invoice_bill_date:
                invoice_vals['invoice_date'] = self.invoice_bill_date
            else:
                invoice_vals['invoice_date'] = fields.Date.today()
            
            # Map invoice_date_due
            if invoice_data.get('invoice_date_due'):
                invoice_vals['invoice_date_due'] = invoice_data['invoice_date_due']
            elif self.due_date:
                invoice_vals['invoice_date_due'] = self.due_date
            
            # Map currency_id - Always use AED for customer invoice migration
            # Log original currency for reference but always use AED
            original_currency = None
            if invoice_data.get('currency_id'):
                currency_id = invoice_data['currency_id']
                if isinstance(currency_id, (list, tuple)) and len(currency_id) > 0:
                    currency_id = currency_id[0]
                original_currency = self.env['res.currency'].search([('id', '=', currency_id)], limit=1)
                if original_currency:
                    _logger.info("📊 Original currency from Odoo 14: %s (ID: %s), but using AED for migration", 
                               original_currency.name, original_currency.id)
            
            # Always use AED for customer invoice migration
            aed_currency = self.env['res.currency'].search([
                '|',
                ('name', '=', 'AED'),
                ('symbol', '=', 'AED')
            ], limit=1)
            
            if aed_currency:
                invoice_vals['currency_id'] = aed_currency.id
                _logger.info("✅ Using AED currency (ID: %s) for invoice %s", aed_currency.id, self.uploaded_invoice_number)
            else:
                # Fallback to company currency if AED not found
                invoice_vals['currency_id'] = company.currency_id.id
                _logger.warning("⚠️ AED currency not found, using company currency: %s", company.currency_id.name)
            
            # Map journal_id
            if invoice_data.get('journal_id'):
                journal_id = invoice_data['journal_id']
                if isinstance(journal_id, (list, tuple)) and len(journal_id) > 0:
                    journal_id = journal_id[0]
                journal = self.env['account.journal'].search([
                    ('id', '=', journal_id),
                    ('type', '=', 'sale')
                ], limit=1)
                if journal:
                    invoice_vals['journal_id'] = journal.id
                else:
                    # Find default sales journal
                    journal = self.env['account.journal'].search([
                        ('type', '=', 'sale'),
                        ('company_id', '=', invoice_vals['company_id'])
                    ], limit=1)
                    if journal:
                        invoice_vals['journal_id'] = journal.id
            else:
                # Find default sales journal
                journal = self.env['account.journal'].search([
                    ('type', '=', 'sale'),
                    ('company_id', '=', invoice_vals['company_id'])
                ], limit=1)
                if journal:
                    invoice_vals['journal_id'] = journal.id
            
            # Store state for later posting (don't set it during creation)
            # Odoo 19 requires creating in draft first, then posting
            should_post = False
            invoice_state = 'draft'
            
            # Priority 1: Check Odoo 14 state
            if invoice_data.get('state'):
                invoice_state = invoice_data['state']
                if invoice_state == 'posted':
                    should_post = True
                    _logger.info("📋 Invoice %s was in 'posted' state in Odoo 14 - will post after creation", self.uploaded_invoice_number)
            
            # Priority 2: Check Excel status if Odoo 14 state not available or not posted
            if not should_post and self.excel_status:
                excel_status_lower = str(self.excel_status).lower()
                if 'posted' in excel_status_lower or 'post' in excel_status_lower:
                    should_post = True
                    _logger.info("📋 Invoice %s has 'Posted' status in Excel - will post after creation", self.uploaded_invoice_number)
            
            # Don't set state in invoice_vals - always create in draft
            # We'll post it later if needed
            
            # Map payment_state (this is computed, but we can set it if needed)
            # Note: payment_state is usually computed, but we can try to preserve it
            # Actually, payment_state is computed, so we don't set it directly
            
            # Map ref
            if invoice_data.get('ref'):
                invoice_vals['ref'] = invoice_data['ref']
            
            # Map narration
            if invoice_data.get('narration'):
                invoice_vals['narration'] = invoice_data['narration']
            
            # Map invoice_origin (for linking to sale order)
            if invoice_data.get('invoice_origin'):
                invoice_vals['invoice_origin'] = invoice_data['invoice_origin']
            
            # Map invoice_payment_term_id
            if invoice_data.get('invoice_payment_term_id'):
                payment_term_id = invoice_data['invoice_payment_term_id']
                if isinstance(payment_term_id, (list, tuple)) and len(payment_term_id) > 0:
                    payment_term_id = payment_term_id[0]
                payment_term = self.env['account.payment.term'].search([('id', '=', payment_term_id)], limit=1)
                if payment_term:
                    invoice_vals['invoice_payment_term_id'] = payment_term.id
            
            # Map fiscal_position_id
            if invoice_data.get('fiscal_position_id'):
                fiscal_position_id = invoice_data['fiscal_position_id']
                if isinstance(fiscal_position_id, (list, tuple)) and len(fiscal_position_id) > 0:
                    fiscal_position_id = fiscal_position_id[0]
                fiscal_position = self.env['account.fiscal.position'].search([('id', '=', fiscal_position_id)], limit=1)
                if fiscal_position:
                    invoice_vals['fiscal_position_id'] = fiscal_position.id
            
            # Map custom fields from eq_fc_invoice_custom
            # location
            if invoice_data.get('location'):
                invoice_vals['location'] = invoice_data['location']
            
            # site_name
            if invoice_data.get('site_name'):
                invoice_vals['site_name'] = invoice_data['site_name']
            
            # create_do
            if invoice_data.get('create_do'):
                invoice_vals['create_do'] = invoice_data['create_do']
            
            # bank_details
            if invoice_data.get('bank_details'):
                invoice_vals['bank_details'] = invoice_data['bank_details']
            
            # file_to_upload and filename
            if invoice_data.get('file_to_upload'):
                invoice_vals['file_to_upload'] = invoice_data['file_to_upload']
            if invoice_data.get('filename'):
                invoice_vals['filename'] = invoice_data['filename']
            
            # in_note
            if invoice_data.get('in_note'):
                invoice_vals['in_note'] = invoice_data['in_note']
            
            # Map custom fields from eq_fc_purchase_custom (if shared)
            # voucher_number (from voucher_no)
            if invoice_data.get('voucher_no'):
                invoice_vals['voucher_number'] = invoice_data['voucher_no']
            elif self.voucher_number:
                invoice_vals['voucher_number'] = self.voucher_number
            
            # is_wo_header
            if invoice_data.get('is_wo_header'):
                invoice_vals['is_wo_header'] = invoice_data['is_wo_header']
            
            # is_with_stamp
            if invoice_data.get('is_with_stamp'):
                invoice_vals['is_with_stamp'] = invoice_data['is_with_stamp']
            
            # quote_reference (Many2one in Odoo 14, Char in Odoo 19)
            if invoice_data.get('quote_reference'):
                quote_ref = invoice_data['quote_reference']
                if isinstance(quote_ref, (list, tuple)) and len(quote_ref) > 1:
                    # Many2one returns [id, name]
                    invoice_vals['quote_reference'] = quote_ref[1]  # Use name
                elif isinstance(quote_ref, (list, tuple)) and len(quote_ref) > 0:
                    # Try to get name from Odoo 14
                    try:
                        quote_id = quote_ref[0]
                        quote_data = client.search_read(
                            'quotation.order',
                            [('id', '=', quote_id)],
                            ['name'],
                            limit=1
                        )
                        if quote_data:
                            invoice_vals['quote_reference'] = quote_data[0].get('name', '')
                    except:
                        pass
                else:
                    invoice_vals['quote_reference'] = str(quote_ref)
            elif self.quote_reference:
                invoice_vals['quote_reference'] = self.quote_reference
            
            # Map user_id (salesperson) - IMPORTANT: Don't default to odoobot
            user_id = None
            if invoice_data.get('user_id'):
                user_id_14 = invoice_data['user_id']
                if isinstance(user_id_14, (list, tuple)) and len(user_id_14) > 0:
                    user_id_14 = user_id_14[0]
                
                # Try to find user in Odoo 19 by ID first
                user = self.env['res.users'].search([('id', '=', user_id_14)], limit=1)
                if not user.exists():
                    # Try to get user info from Odoo 14 and find by login/name/email
                    try:
                        user_data = client.search_read(
                            'res.users',
                            [('id', '=', user_id_14)],
                            ['login', 'name', 'email'],
                            limit=1
                        )
                        if user_data:
                            user_info = user_data[0]
                            # Search for user in Odoo 19 by login (most reliable)
                            if user_info.get('login'):
                                user = self.env['res.users'].search([
                                    ('login', '=', user_info.get('login'))
                                ], limit=1)
                            # If not found by login, try by name
                            if not user.exists() and user_info.get('name'):
                                user = self.env['res.users'].search([
                                    ('name', '=', user_info.get('name'))
                                ], limit=1)
                            # If still not found, try by email
                            if not user.exists() and user_info.get('email'):
                                user = self.env['res.users'].search([
                                    ('email', '=', user_info.get('email'))
                                ], limit=1)
                    except Exception as e:
                        _logger.warning("Could not fetch user from Odoo 14: %s", str(e))
                
                if user.exists():
                    invoice_vals['user_id'] = user.id
                    _logger.info("✅ Mapped salesperson: %s (ID: %s) for invoice %s", user.name, user.id, self.uploaded_invoice_number)
                else:
                    _logger.warning("⚠️ Could not find user (ID: %s) in Odoo 19, invoice will have no salesperson", user_id_14)
            
            # Link to sale order if available
            sale_order = False
            if invoice_data.get('sale_id'):
                sale_id = invoice_data['sale_id']
                if isinstance(sale_id, (list, tuple)) and len(sale_id) > 0:
                    sale_id = sale_id[0]
                sale_order = self.env['sale.order'].search([('id', '=', sale_id)], limit=1)
                if sale_order:
                    invoice_vals['sale_id'] = sale_order.id
                    # If user_id not set, try to get from sale order
                    if not invoice_vals.get('user_id') and sale_order.user_id:
                        invoice_vals['user_id'] = sale_order.user_id.id
                        _logger.info("✅ Set salesperson from sale order: %s (ID: %s)", sale_order.user_id.name, sale_order.user_id.id)
            elif invoice_vals.get('invoice_origin'):
                # Try to find sale order by invoice_origin
                sale_order = self.env['sale.order'].search([
                    ('name', '=', invoice_vals['invoice_origin'])
                ], limit=1)
                if sale_order:
                    invoice_vals['sale_id'] = sale_order.id
                    # If user_id not set, try to get from sale order
                    if not invoice_vals.get('user_id') and sale_order.user_id:
                        invoice_vals['user_id'] = sale_order.user_id.id
                        _logger.info("✅ Set salesperson from sale order (by origin): %s (ID: %s)", sale_order.user_id.name, sale_order.user_id.id)
            elif invoice_vals.get('quote_reference'):
                # Try to find sale order by quote_reference
                sale_order = self.env['sale.order'].search([
                    ('name', '=', invoice_vals['quote_reference'])
                ], limit=1)
                if sale_order:
                    invoice_vals['sale_id'] = sale_order.id
                    # If user_id not set, try to get from sale order
                    if not invoice_vals.get('user_id') and sale_order.user_id:
                        invoice_vals['user_id'] = sale_order.user_id.id
                        _logger.info("✅ Set salesperson from sale order (by quote ref): %s (ID: %s)", sale_order.user_id.name, sale_order.user_id.id)
            
            # Create invoice in Odoo 19 (always in draft state)
            # Remove state from vals if present to ensure draft creation
            if 'state' in invoice_vals:
                del invoice_vals['state']
            
            invoice = self.env['account.move'].create(invoice_vals)
            _logger.info("✅ Created invoice %s in draft state (ID: %s)", invoice.name, invoice.id)
            
            # Preserve original creation date and user
            src_create_date = invoice_data.get('create_date')
            src_write_date = invoice_data.get('write_date')
            src_create_uid = invoice_data.get('create_uid')
            src_write_uid = invoice_data.get('write_uid')
            
            if src_create_date or src_write_date or src_create_uid or src_write_uid:
                try:
                    update_sql = "UPDATE account_move SET"
                    params = []
                    if src_create_date:
                        update_sql += " create_date = %s,"
                        params.append(src_create_date)
                    if src_write_date:
                        update_sql += " write_date = %s,"
                        params.append(src_write_date)
                    if src_create_uid:
                        if isinstance(src_create_uid, (list, tuple)):
                            src_create_uid = src_create_uid[0]
                        # Find user in Odoo 19
                        user = self.env['res.users'].search([('id', '=', src_create_uid)], limit=1)
                        if not user:
                            # Try by login or name
                            try:
                                user_data = client.search_read(
                                    'res.users',
                                    [('id', '=', src_create_uid)],
                                    ['login', 'name', 'email'],
                                    limit=1
                                )
                                if user_data:
                                    user = self.env['res.users'].search([
                                        '|', '|',
                                        ('login', '=', user_data[0].get('login')),
                                        ('name', '=', user_data[0].get('name')),
                                        ('email', '=', user_data[0].get('email'))
                                    ], limit=1)
                            except:
                                pass
                        if user:
                            update_sql += " create_uid = %s,"
                            params.append(user.id)
                    if src_write_uid:
                        if isinstance(src_write_uid, (list, tuple)):
                            src_write_uid = src_write_uid[0]
                        user = self.env['res.users'].search([('id', '=', src_write_uid)], limit=1)
                        if not user:
                            try:
                                user_data = client.search_read(
                                    'res.users',
                                    [('id', '=', src_write_uid)],
                                    ['login', 'name', 'email'],
                                    limit=1
                                )
                                if user_data:
                                    user = self.env['res.users'].search([
                                        '|', '|',
                                        ('login', '=', user_data[0].get('login')),
                                        ('name', '=', user_data[0].get('name')),
                                        ('email', '=', user_data[0].get('email'))
                                    ], limit=1)
                            except:
                                pass
                        if user:
                            update_sql += " write_uid = %s,"
                            params.append(user.id)
                    
                    update_sql = update_sql.rstrip(',')
                    update_sql += " WHERE id = %s"
                    params.append(invoice.id)
                    
                    self.env.cr.execute(update_sql, params)
                except Exception as e:
                    _logger.warning("Could not set original dates/users: %s", str(e))
            
            # Migrate invoice lines
            line_ids_to_migrate = []
            if invoice_data.get('invoice_line_ids'):
                line_ids = invoice_data['invoice_line_ids']
                if isinstance(line_ids, (list, tuple)):
                    line_ids_to_migrate = [lid for lid in line_ids if isinstance(lid, int)]
            
            if line_ids_to_migrate:
                try:
                    for line_id in line_ids_to_migrate:
                        try:
                            line_data = client.search_read(
                                'account.move.line',
                                [('id', '=', line_id), ('move_id', '=', invoice_data['id'])],
                                ['product_id', 'name', 'quantity', 'price_unit', 'discount', 'tax_ids', 
                                 'account_id', 'sequence', 'sale_line_ids', 'brand_id', 'display_type', 'tax_line_id'],
                                limit=1
                            )
                            if line_data:
                                line_info = line_data[0]
                                
                                # FILTER: Skip section headers and notes
                                if line_info.get('display_type') in ('line_section', 'line_note'):
                                    continue
                                    
                                # FILTER: Skip auto-generated tax lines
                                if line_info.get('tax_line_id'):
                                    continue
                                
                                # FILTER: Skip lines with 0 quantity AND 0 price (unless it's 100% discount, but usually junk)
                                if line_info.get('quantity', 0) == 0 and line_info.get('price_unit', 0) == 0:
                                     continue
                                
                                line_vals = {
                                    'move_id': invoice.id,
                                    'name': line_info.get('name', '') or 'Line',
                                    'quantity': line_info.get('quantity', 1.0),
                                    'price_unit': line_info.get('price_unit', 0.0),
                                    'discount': line_info.get('discount', 0.0),
                                }
                                
                                if line_info.get('sequence'):
                                    line_vals['sequence'] = line_info['sequence']
                                
                                # Map product_id
                                if line_info.get('product_id'):
                                    product_id = line_info['product_id']
                                    if isinstance(product_id, (list, tuple)) and len(product_id) > 0:
                                        product_id = product_id[0]
                                    product = self.env['product.product'].search([('id', '=', product_id)], limit=1)
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
                                                if prod_data.get('default_code'):
                                                    product = self.env['product.product'].search([
                                                        ('default_code', '=', prod_data['default_code'])
                                                    ], limit=1)
                                                if not product and prod_data.get('name'):
                                                    product = self.env['product.product'].search([
                                                        ('name', '=', prod_data['name'])
                                                    ], limit=1)
                                                if not product and prod_data.get('barcode'):
                                                    product = self.env['product.product'].search([
                                                        ('barcode', '=', prod_data['barcode'])
                                                    ], limit=1)
                                                if not product:
                                                    product_vals = {
                                                        'name': prod_data.get('name', 'Migrated Product'),
                                                        'type': 'consu',
                                                    }
                                                    if prod_data.get('default_code'):
                                                        product_vals['default_code'] = prod_data['default_code']
                                                    product = self.env['product.product'].create(product_vals)
                                        except:
                                            pass
                                    if product:
                                        line_vals['product_id'] = product.id
                                
                                # Map account_id - ENFORCED RULE: Always use "401100 Sales Account"
                                # Search for the specific sales account in the target company
                                account_code = '401100'
                                account = self.env['account.account'].search([
                                    ('code', '=', account_code),
                                    ('company_id', '=', invoice.company_id.id),
                                    ('deprecated', '=', False)
                                ], limit=1)
                                
                                if not account:
                                    _logger.warning("⚠️ CRITICAL: Enforced Sales Account '%s' not found for company '%s'! Falling back to default search...", 
                                                  account_code, invoice.company_id.name)
                                    # Fallback to old logic only if enforced account is missing
                                    if line_info.get('account_id'):
                                        account_id = line_info['account_id']
                                        if isinstance(account_id, (list, tuple)) and len(account_id) > 0:
                                            account_id = account_id[0]
                                        account = self.env['account.account'].search([('id', '=', account_id)], limit=1)
                                    
                                    if not account and line_vals.get('product_id'):
                                        product = self.env['product.product'].browse(line_vals['product_id'])
                                        if product.property_account_income_id:
                                            account = product.property_account_income_id
                                            
                                    if not account:
                                        default_account = self.env['account.account'].search([
                                            ('company_id', '=', invoice.company_id.id),
                                            ('deprecated', '=', False),
                                            ('internal_group', '=', 'income')
                                        ], limit=1, order='code asc')
                                        if default_account:
                                            account = default_account
                                
                                if account:
                                    line_vals['account_id'] = account.id
                                    _logger.info("   Using account: %s %s", account.code, account.name)
                                else:
                                    _logger.warning("❌ Could not find ANY account for invoice line!")
                                
                                # Map tax_ids
                                if line_info.get('tax_ids'):
                                    tax_ids = line_info['tax_ids']
                                    if isinstance(tax_ids, (list, tuple)):
                                        tax_ids = [tid for tid in tax_ids if isinstance(tid, int)]
                                    if tax_ids:
                                        taxes = self.env['account.tax'].search([('id', 'in', tax_ids)])
                                        if taxes:
                                            line_vals['tax_ids'] = [(6, 0, taxes.ids)]
                                
                                # Map sale_line_ids for linking to sale order lines
                                if line_info.get('sale_line_ids') and invoice_vals.get('sale_id'):
                                    sale_line_ids = line_info['sale_line_ids']
                                    if isinstance(sale_line_ids, (list, tuple)):
                                        sale_line_ids = [slid for slid in sale_line_ids if isinstance(slid, int)]
                                    if sale_line_ids and sale_order:
                                        sale_lines = self.env['sale.order.line'].search([
                                            ('id', 'in', sale_line_ids),
                                            ('order_id', '=', sale_order.id)
                                        ])
                                        if sale_lines:
                                            line_vals['sale_line_ids'] = [(6, 0, sale_lines.ids)]
                                
                                self.env['account.move.line'].create(line_vals)
                        except Exception as e:
                            _logger.warning("Could not migrate invoice line %s: %s", line_id, str(e), exc_info=True)
                except Exception as e:
                    _logger.warning("Could not migrate invoice lines: %s", str(e), exc_info=True)
            
            self.env.cr.commit()
            
            # Post invoice if it should be posted (from Odoo 14 state or Excel status)
            # IMPORTANT: Create in draft first, then post if needed
            if should_post:
                try:
                    _logger.info("📝 Posting invoice %s (was in posted state in Odoo 14 or Excel)", invoice.name)
                    # Ensure invoice is in draft before posting
                    if invoice.state != 'draft':
                        _logger.warning("⚠️ Invoice %s is not in draft state (%s), resetting to draft", invoice.name, invoice.state)
                        invoice.button_draft()
                        self.env.cr.commit()
                    
                    # Post the invoice
                    invoice.action_post()
                    self.env.cr.commit()
                    _logger.info("✅ Successfully posted invoice %s", invoice.name)
                except Exception as e:
                    _logger.warning("⚠️ Could not post invoice %s: %s", invoice.name, str(e))
                    # Don't fail the migration if posting fails - invoice is still created in draft
                    # Just log the warning
            
            # Update status to migrated
            self.write({
                'status': 'migrated',
                'status_message': 'Successfully migrated',
                'odoo19_invoice_id': invoice.id,
                'odoo19_sale_order_id': sale_order.id if sale_order else False,
                'in_system_invoice_number': invoice.name,
                'migration_date': fields.Datetime.now(),
                'error_message': False,
            })
            self.env.cr.commit()
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'customer.invoice.migration.line',
                'view_mode': 'list,form',
                'target': 'current',
            }
                
        except UserError:
            raise
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error in action_migrate: %s", error_msg, exc_info=True)
            self.write({
                'status': 'error',
                'status_message': 'Error: %s' % error_msg,
                'error_message': error_msg,
            })
            self.env.cr.commit()
            _log_failed_invoice_migration(self.uploaded_invoice_number, error_msg)
            raise UserError('Error migrating invoice: %s' % str(e))
    
    def _migrate_sequential(self, record_ids, current_index):
        """Sequential migration method using Queue Jobs"""
        if current_index >= len(record_ids):
            _logger.info("Sequential migration completed for all %s records", len(record_ids))
            return
        
        record_id = record_ids[current_index]
        record = self.env['customer.invoice.migration.line'].browse(record_id)
        
        if not record.exists():
            _logger.warning("Record %s does not exist, skipping", record_id)
            if current_index + 1 < len(record_ids):
                next_record = record.env['customer.invoice.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        invoice_number = record.uploaded_invoice_number
        _logger.info("🚀 Starting migration %s/%s: %s (record_id=%s)", current_index + 1, len(record_ids), invoice_number, record_id)
        
        if record.status not in ('pending_migration', 'queued'):
            _logger.warning("Record %s is not in pending_migration or queued status (%s), skipping", invoice_number, record.status)
            if current_index + 1 < len(record_ids):
                next_record = record.env['customer.invoice.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        if not record.config_id:
            record.write({
                'status': 'error',
                'status_message': 'Migration configuration is required',
                'error_message': 'Migration configuration is required',
            })
            record.env.flush_all()
            
            if current_index + 1 < len(record_ids):
                next_record = record.env['customer.invoice.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        record.write({
            'status': 'migrating',
            'status_message': 'Migration in progress...',
        })
        record.env.flush_all()
        _logger.info("📝 Status updated to 'migrating' for %s", invoice_number)
        
        try:
            record.action_migrate()
            _logger.info("✅ Successfully migrated %s (%s/%s)", invoice_number, current_index + 1, len(record_ids))
        except Exception as e:
            error_msg = str(e)
            _logger.error("❌ Error migrating invoice %s: %s", invoice_number, error_msg, exc_info=True)
            
            try:
                record.write({
                    'status': 'error',
                    'status_message': 'Migration failed',
                    'error_message': error_msg[:500] if len(error_msg) > 500 else error_msg,
                })
                record.env.flush_all()
            except Exception as status_error:
                _logger.error("❌ Failed to update error status: %s", str(status_error))
        
        record.env.flush_all()
        
        if current_index + 1 < len(record_ids):
            next_index = current_index + 1
            next_record_id = record_ids[next_index]
            _logger.info("🔄 Enqueueing next migration (%s/%s): record_id=%s", next_index + 1, len(record_ids), next_record_id)
            
            try:
                fresh_env = record.env
                next_record = fresh_env['customer.invoice.migration.line'].browse(next_record_id)
                
                if not next_record.exists():
                    _logger.error("Next record %s does not exist, stopping sequential migration", next_record_id)
                    return
                
                job = next_record.with_delay()._migrate_sequential(record_ids, next_index)
                _logger.info("✅ Next job enqueued: job_uuid=%s, record_id=%s", getattr(job, 'uuid', 'N/A'), next_record_id)
                
                import time
                time.sleep(0.3)
                
            except Exception as e:
                _logger.error("❌ Failed to enqueue next migration job: %s", str(e), exc_info=True)
        else:
            _logger.info("✅ All migrations completed!")

