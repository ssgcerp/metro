# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
from datetime import datetime
import time

_logger = logging.getLogger(__name__)


def _log_failed_bill_migration(bill_number, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_vendor_bill_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {bill_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed vendor bill migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed migrations log: %s", str(e))


def _retry_on_serialization_error(func, max_retries=3, initial_delay=0.1):
    """
    Retry a function on PostgreSQL serialization errors with exponential backoff.
    
    Args:
        func: Function to retry (should be a callable)
        max_retries: Maximum number of retries (default: 3)
        initial_delay: Initial delay in seconds (default: 0.1)
    
    Returns:
        Result of the function call
    
    Raises:
        Exception: If all retries fail
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
                # Not a serialization error or max retries reached
                raise


def _search_account_safe(env, domain, company_id=None, limit=1, order=None):
    """
    Safely search for accounts, handling the case where 'deprecated' field might not exist.
    
    Args:
        env: Odoo environment
        domain: Search domain (list of tuples)
        company_id: Company ID to use with_company context
        limit: Limit for search
        order: Order clause
    
    Returns:
        account.account recordset
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


class VendorBillMigrationLine(models.Model):
    """Model to store uploaded vendor bill numbers and track migration status"""
    _name = 'vendor.bill.migration.line'
    _description = 'Vendor Bill Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    uploaded_bill_number = fields.Char(
        string='Number',
        required=True,
        index=True,
        help='Vendor bill number from Excel upload'
    )
    
    in_system_bill_number = fields.Char(
        string='In-System Bill Number',
        readonly=True,
        help='Actual bill number found in Odoo 14 or Odoo 19'
    )
    
    # Additional fields from Excel
    voucher_number = fields.Char(
        string='Voucher Number',
        help='Voucher number from Excel'
    )
    
    bill_partner_name = fields.Char(
        string='Bill Partner Name',
        help='Vendor/Partner name from Excel'
    )
    
    invoice_bill_date = fields.Date(
        string='Invoice/Bill Date',
        help='Bill date from Excel'
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
    
    # State and payment_state from Odoo 14
    odoo14_state = fields.Char(
        string='State (Odoo 14)',
        readonly=True,
        help='Posted/Draft status from Odoo 14'
    )
    
    odoo14_payment_state = fields.Char(
        string='Payment State (Odoo 14)',
        readonly=True,
        help='Payment status from Odoo 14 (not_paid, partial, paid, etc.)'
    )
    
    company = fields.Char(
        string='Company',
        help='Company/Branch name from Excel'
    )
    
    lpo_number = fields.Char(
        string='LPO Number',
        help='LPO number from Excel'
    )
    
    po_number = fields.Char(
        string='PO Number',
        help='PO number from Excel'
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
    
    odoo14_bill_id = fields.Integer(
        string='Odoo 14 Bill ID',
        readonly=True,
        help='ID of vendor bill in Odoo 14 if found'
    )
    
    odoo19_bill_id = fields.Many2one(
        'account.move',
        string='Odoo 19 Vendor Bill',
        readonly=True,
        domain=[('move_type', '=', 'in_invoice')],
        help='Migrated vendor bill in Odoo 19'
    )
    
    odoo19_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Linked Purchase Order',
        readonly=True,
        help='Linked purchase order in Odoo 19'
    )
    
    migration_date = fields.Datetime(string='Migration Date', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    
    total_items_odoo14 = fields.Integer(
        string='Total Items (Odoo 14)',
        readonly=True,
        help='Total number of invoice lines found in Odoo 14'
    )
    
    total_items_odoo19 = fields.Integer(
        string='Total Items Migrated',
        readonly=True,
        help='Total number of invoice lines successfully migrated to Odoo 19'
    )

    def check_status(self, bill_number=None, config_id=None):
        """Check status of a vendor bill number against Odoo 14 and Odoo 19"""
        self.ensure_one()
        if not bill_number:
            bill_number = self.uploaded_bill_number
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
                ('name', '=', bill_number),
                ('move_type', '=', 'in_invoice')
            ], limit=1)
            
            if existing_19:
                return {
                    'status': 'already_migrated',
                    'message': 'Already exists in Odoo 19',
                    'odoo19_id': existing_19.id,
                    'odoo19_name': existing_19.name
                }
            
            # Check in Odoo 14
            bills = []
            try:
                bills = client.search_read(
                    'account.move',
                    [('name', '=', bill_number), ('move_type', '=', 'in_invoice')],
                    ['id', 'name'],
                    limit=1
                )
            except Exception as e:
                _logger.debug("Error checking Odoo 14: %s", str(e))
            
            if bills:
                return {
                    'status': 'pending_migration',
                    'message': 'Found in Odoo 14, ready to migrate',
                    'odoo14_id': bills[0]['id'],
                    'odoo14_name': bills[0]['name']
                }
            else:
                return {
                    'status': 'not_found',
                    'message': 'Not found in Odoo 14'
                }
                
        except Exception as e:
            _logger.error("Error checking vendor bill status: %s", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def action_check_status(self):
        """Button action to refresh status"""
        for record in self:
            result = record.check_status()
            record.write({
                'status': result.get('status', 'not_found'),
                'status_message': result.get('message', ''),
                'in_system_bill_number': result.get('odoo14_name') or result.get('odoo19_name') or '',
                'odoo14_bill_id': result.get('odoo14_id', 0),
                'odoo19_bill_id': result.get('odoo19_id', False),
            })
    
    @api.model
    def action_open_upload_wizard(self):
        """Open the Excel upload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.bill.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': 'Upload Excel',
        }
    
    def action_bulk_migrate(self):
        """Bulk migrate selected vendor bills sequentially using Queue Jobs"""
        try:
            pending = self.filtered(lambda l: l.status == 'pending_migration')
            if not pending:
                raise UserError('No vendor bills with "Pending Migration" status selected')
            
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
                raise UserError('No vendor bills with "Pending Migration" status selected')
            
            fresh_pending = self.env['vendor.bill.migration.line'].browse(pending_ids)
            for record in fresh_pending:
                record.write({
                    'status': 'queued',
                    'status_message': 'Queued for migration - waiting to be processed',
                    'error_message': False,
                })
            self.env.cr.commit()
            _logger.info("✅ Marked %s vendor bills as 'queued' (ready for processing)", len(fresh_pending))
        
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Vendor Bills Queued',
                    'message': f'{len(pending_ids)} vendor bills have been queued. Use "Start Queued Migration" to start the migration process.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error in action_bulk_migrate: %s", str(e), exc_info=True)
            raise UserError(f'Error queuing vendor bills: {str(e)}')
    
    def action_start_queued_migration(self):
        """Start processing queued vendor bills - enqueue the first job to start sequential migration"""
        queued = self.filtered(lambda l: l.status == 'queued')
        if not queued:
            raise UserError('No vendor bills with "Queued" status selected')
        
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
            raise UserError('No vendor bills with "Queued" status selected')
        
        try:
            first_record = self.browse(queued_ids[0])
            if not first_record.exists():
                raise UserError(f'Record {queued_ids[0]} no longer exists')
            
            job = first_record.with_delay()._migrate_sequential(queued_ids, 0)
            
            _logger.info("✅ Started sequential migration for %s queued vendor bills (job UUID: %s)", 
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
                    'message': f'Started processing {len(queued_ids)} queued vendor bills. Migration will continue sequentially.',
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
    
    def _find_or_create_purchase_journal(self, company):
        """
        Find or create a purchase journal for the given company.
        
        Args:
            company: res.company record
            
        Returns:
            account.journal record or False if not found/created
        """
        # First, try to find any purchase journal for the company
        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', company.id)
        ], limit=1)
        
        if journal:
            _logger.info("✅ Found existing purchase journal '%s' (ID: %s) for company '%s'", 
                        journal.name, journal.id, company.name)
            return journal
        
        # Try to find a purchase journal from another company as template
        template_journal = self.env['account.journal'].search([
            ('type', '=', 'purchase')
        ], limit=1)
        
        if template_journal:
            _logger.info("📋 Found template purchase journal '%s' (ID: %s) from company '%s'", 
                       template_journal.name, template_journal.id, template_journal.company_id.name)
        
        # Try to create a default purchase journal
        try:
            # Get default expense account for the company
            default_account = _search_account_safe(
                self.env,
                [('internal_group', '=', 'expense')],
                company_id=company.id,
                limit=1,
                order='code asc'
            )
            
            if not default_account:
                # Try to find any account for the company
                default_account = _search_account_safe(
                    self.env,
                    [],
                    company_id=company.id,
                    limit=1,
                    order='code asc'
                )
            
            # Try to find account with code 501100 (PURCHASE EXPENSES) for the company
            purchase_expense_account = _search_account_safe(
                self.env,
                [('code', '=', '501100')],
                company_id=company.id,
                limit=1
            )
            
            if purchase_expense_account:
                default_account = purchase_expense_account
                _logger.info("✅ Found PURCHASE EXPENSES account (501100) for company '%s'", company.name)
            elif not default_account:
                # If no 501100 account, try to find any expense account
                default_account = _search_account_safe(
                    self.env,
                    [('internal_group', '=', 'expense')],
                    company_id=company.id,
                    limit=1,
                    order='code asc'
                )
            
            journal_vals = {
                'name': f'Purchase - {company.name}',
                'code': 'PURCH',
                'type': 'purchase',
                'company_id': company.id,
            }
            
            if default_account:
                journal_vals['default_account_id'] = default_account.id
                _logger.info("✅ Setting default account '%s' (code: %s) for purchase journal", 
                           default_account.name, default_account.code)
            
            # Try to get default sequence
            if template_journal and template_journal.sequence_id:
                # Create a new sequence based on template
                sequence_vals = {
                    'name': f'Purchase Journal Sequence - {company.name}',
                    'code': f'account.journal.purchase.{company.id}',
                    'company_id': company.id,
                    'prefix': 'PURCH',
                    'padding': 5,
                }
                sequence = self.env['ir.sequence'].create(sequence_vals)
                journal_vals['sequence_id'] = sequence.id
            
            journal = self.env['account.journal'].create(journal_vals)
            _logger.info("✅ Created purchase journal '%s' (ID: %s) for company '%s'", 
                        journal.name, journal.id, company.name)
            return journal
            
        except Exception as e:
            _logger.error("❌ Failed to create purchase journal for company '%s': %s", company.name, str(e), exc_info=True)
            return False
    
    def _find_or_create_payment_journal(self, company, payment_type='inbound'):
        """
        Find or create a payment journal for the given company.
        
        Args:
            company: res.company record
            payment_type: 'inbound' for customer payments, 'outbound' for vendor payments
            
        Returns:
            account.journal record or False if not found/created
        """
        # For vendor bills, we need outbound payment journal (paying vendors)
        journal_type = 'bank'  # Payment journals are typically bank journals
        journal_name = f'Bank - {company.name}' if payment_type == 'outbound' else f'Bank - {company.name}'
        
        # First, try to find any bank journal for the company
        journal = self.env['account.journal'].search([
            ('type', '=', journal_type),
            ('company_id', '=', company.id)
        ], limit=1)
        
        if journal:
            _logger.info("✅ Found existing bank journal '%s' (ID: %s) for company '%s'", 
                        journal.name, journal.id, company.name)
            return journal
        
        # Try to find a bank journal from another company as template
        template_journal = self.env['account.journal'].search([
            ('type', '=', journal_type)
        ], limit=1)
        
        if template_journal:
            _logger.info("📋 Found template bank journal '%s' (ID: %s) from company '%s'", 
                       template_journal.name, template_journal.id, template_journal.company_id.name)
        
        # Try to create a default bank journal
        try:
            # Get default account for the company (bank account or cash account)
            default_account = _search_account_safe(
                self.env,
                [('account_type', 'in', ['asset_cash', 'asset_current'])],
                company_id=company.id,
                limit=1,
                order='code asc'
            )
            
            if not default_account:
                # Try to find any asset account
                default_account = _search_account_safe(
                    self.env,
                    [('account_type', '=', 'asset_current')],
                    company_id=company.id,
                    limit=1,
                    order='code asc'
                )
            
            journal_vals = {
                'name': journal_name,
                'code': 'BNK',
                'type': journal_type,
                'company_id': company.id,
            }
            
            if default_account:
                journal_vals['default_account_id'] = default_account.id
            
            # Try to get default sequence
            if template_journal and template_journal.sequence_id:
                # Create a new sequence based on template
                sequence_vals = {
                    'name': f'Bank Journal Sequence - {company.name}',
                    'code': f'account.journal.bank.{company.id}',
                    'company_id': company.id,
                    'prefix': 'BNK',
                    'padding': 5,
                }
                sequence = self.env['ir.sequence'].create(sequence_vals)
                journal_vals['sequence_id'] = sequence.id
            
            journal = self.env['account.journal'].create(journal_vals)
            _logger.info("✅ Created bank journal '%s' (ID: %s) for company '%s'", 
                        journal.name, journal.id, company.name)
            return journal
            
        except Exception as e:
            _logger.error("❌ Failed to create bank journal for company '%s': %s", company.name, str(e), exc_info=True)
            return False
    
    def _fetch_payments_from_odoo14(self, client, bill_id_odoo14):
        """
        Fetch payments linked to a vendor bill from Odoo 14.
        
        Args:
            client: Odoo14APIClient instance
            bill_id_odoo14: ID of the bill in Odoo 14
            
        Returns:
            List of payment dictionaries
        """
        payments = []
        
        try:
            # Check if account.payment model exists in Odoo 14
            if client.check_model_exists('account.payment'):
                # Try to find payments linked via reconciled_invoice_ids
                try:
                    payment_records = client.search_read(
                        'account.payment',
                        [('state', '=', 'posted')],
                        ['name', 'date', 'amount', 'payment_type', 'partner_id', 
                         'journal_id', 'reconciled_invoice_ids', 'ref', 'company_id'],
                        limit=1000  # Large limit to find all payments
                    )
                    
                    # Filter payments that are linked to this bill
                    for payment in payment_records:
                        reconciled_invoice_ids = payment.get('reconciled_invoice_ids', [])
                        if isinstance(reconciled_invoice_ids, list):
                            # Extract IDs from many2many format [id, name] or just id
                            invoice_ids = []
                            for inv_id in reconciled_invoice_ids:
                                if isinstance(inv_id, int):
                                    invoice_ids.append(inv_id)
                                elif isinstance(inv_id, (list, tuple)) and len(inv_id) > 0:
                                    invoice_ids.append(inv_id[0])
                            
                            if bill_id_odoo14 in invoice_ids:
                                payments.append(payment)
                                _logger.info("✅ Found payment '%s' (ID: %s) linked to bill %s", 
                                           payment.get('name', 'N/A'), payment.get('id'), bill_id_odoo14)
                except Exception as e:
                    _logger.warning("⚠️ Could not fetch payments via account.payment: %s", str(e))
            
            # Also check account.move.line for payment entries (reconciliation)
            try:
                # Find reconciled lines for this bill
                bill_lines = client.search_read(
                    'account.move.line',
                    [('move_id', '=', bill_id_odoo14), ('reconciled', '=', True)],
                    ['full_reconcile_id', 'move_id'],
                    limit=100
                )
                
                for bill_line in bill_lines:
                    full_reconcile_id = bill_line.get('full_reconcile_id')
                    if full_reconcile_id:
                        if isinstance(full_reconcile_id, (list, tuple)):
                            full_reconcile_id = full_reconcile_id[0]
                        
                        # Find other lines in the same reconciliation
                        reconciled_lines = client.search_read(
                            'account.move.line',
                            [('full_reconcile_id', '=', full_reconcile_id), ('move_id', '!=', bill_id_odoo14)],
                            ['move_id', 'balance', 'account_id'],
                            limit=100
                        )
                        
                        for rec_line in reconciled_lines:
                            payment_move_id = rec_line.get('move_id')
                            if isinstance(payment_move_id, (list, tuple)):
                                payment_move_id = payment_move_id[0]
                            
                            # Get the payment move details
                            payment_moves = client.search_read(
                                'account.move',
                                [('id', '=', payment_move_id)],
                                ['name', 'date', 'move_type', 'state', 'journal_id', 'partner_id', 'company_id'],
                                limit=1
                            )
                            
                            if payment_moves:
                                payment_move = payment_moves[0]
                                # Check if it's a payment entry
                                if payment_move.get('move_type') == 'entry' and payment_move.get('state') == 'posted':
                                    # Calculate payment amount from reconciled lines
                                    payment_amount = abs(float(rec_line.get('balance', 0)))
                                    
                                    payment_info = {
                                        'name': payment_move.get('name', ''),
                                        'date': payment_move.get('date', ''),
                                        'amount': payment_amount,
                                        'id': payment_move_id,
                                        'journal_id': payment_move.get('journal_id'),
                                        'partner_id': payment_move.get('partner_id'),
                                        'company_id': payment_move.get('company_id'),
                                        'ref': payment_move.get('name', ''),
                                        'payment_type': 'outbound',  # Vendor payments are outbound
                                        'source': 'reconciliation'  # Mark as from reconciliation
                                    }
                                    
                                    # Check if we already have this payment
                                    if not any(p.get('id') == payment_move_id for p in payments):
                                        payments.append(payment_info)
                                        _logger.info("✅ Found payment via reconciliation: '%s' (ID: %s, Amount: %s)", 
                                                   payment_info.get('name'), payment_move_id, payment_amount)
            except Exception as e:
                _logger.warning("⚠️ Could not fetch payments via reconciliation: %s", str(e))
                
        except Exception as e:
            _logger.warning("⚠️ Error fetching payments from Odoo 14: %s", str(e), exc_info=True)
        
        _logger.info("📋 Found %s payment(s) linked to bill %s in Odoo 14", len(payments), bill_id_odoo14)
        return payments
    
    def _migrate_payments(self, client, bill, payments_odoo14):
        """
        Migrate payments from Odoo 14 to Odoo 19 and link them to the migrated bill.
        
        Args:
            client: Odoo14APIClient instance
            bill: account.move record (the migrated vendor bill)
            payments_odoo14: List of payment dictionaries from Odoo 14
            
        Returns:
            List of created payment IDs
        """
        if not payments_odoo14:
            _logger.info("📋 No payments to migrate for bill %s", bill.name)
            return []
        
        created_payments = []
        
        for payment_data in payments_odoo14:
            try:
                payment_name = payment_data.get('name', '')
                payment_amount = float(payment_data.get('amount', 0.0))
                payment_date = payment_data.get('date', '')
                payment_id_odoo14 = payment_data.get('id')
                
                _logger.info("💳 Migrating payment '%s' (ID: %s, Amount: %s) for bill %s", 
                           payment_name, payment_id_odoo14, payment_amount, bill.name)
                
                # Extract partner_id
                partner_id = payment_data.get('partner_id')
                if isinstance(partner_id, (list, tuple)) and len(partner_id) > 0:
                    partner_id = partner_id[0]
                
                # Use bill's partner if payment partner not found
                if not partner_id:
                    partner_id = bill.partner_id.id
                    _logger.warning("⚠️ Payment has no partner, using bill's partner: %s", bill.partner_id.name)
                else:
                    # Verify partner exists in Odoo 19
                    partner = self.env['res.partner'].search([('id', '=', partner_id)], limit=1)
                    if not partner:
                        _logger.warning("⚠️ Partner ID %s not found in Odoo 19, using bill's partner", partner_id)
                        partner_id = bill.partner_id.id
                
                # Extract journal_id
                journal_id = payment_data.get('journal_id')
                if isinstance(journal_id, (list, tuple)) and len(journal_id) > 0:
                    journal_id = journal_id[0]
                
                # Find or create payment journal for the company
                if journal_id:
                    journal = self.env['account.journal'].search([
                        ('id', '=', journal_id),
                        ('type', 'in', ['bank', 'cash']),
                        ('company_id', '=', bill.company_id.id)
                    ], limit=1)
                    
                    if not journal:
                        _logger.warning("⚠️ Payment journal ID %s not found or company mismatch, finding default", journal_id)
                        journal = self._find_or_create_payment_journal(bill.company_id, payment_type='outbound')
                else:
                    journal = self._find_or_create_payment_journal(bill.company_id, payment_type='outbound')
                
                if not journal:
                    _logger.error("❌ Could not find or create payment journal for company '%s', skipping payment", 
                                bill.company_id.name)
                    continue
                
                # Parse payment date
                payment_date_obj = False
                if payment_date:
                    try:
                        from datetime import datetime
                        if isinstance(payment_date, str):
                            # Try different date formats
                            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y']:
                                try:
                                    payment_date_obj = datetime.strptime(payment_date.split()[0], fmt).date()
                                    break
                                except:
                                    continue
                        if not payment_date_obj:
                            payment_date_obj = fields.Date.today()
                    except:
                        payment_date_obj = fields.Date.today()
                else:
                    payment_date_obj = fields.Date.today()
                
                # Create payment record
                payment_vals = {
                    'payment_type': 'outbound',  # Vendor payments are outbound
                    'partner_type': 'supplier',
                    'partner_id': partner_id,
                    'amount': payment_amount,
                    'currency_id': bill.currency_id.id,
                    'payment_date': payment_date_obj,
                    'journal_id': journal.id,
                    'company_id': bill.company_id.id,
                    'ref': payment_data.get('ref', payment_name),
                }
                
                # Create payment
                payment = self.env['account.payment'].with_company(bill.company_id.id).create(payment_vals)
                _logger.info("✅ Created payment '%s' (ID: %s) for bill %s", payment.name, payment.id, bill.name)
                
                # Post the payment
                try:
                    payment.action_post()
                    self.env.cr.commit()
                    _logger.info("✅ Posted payment '%s'", payment.name)
                except Exception as e:
                    _logger.warning("⚠️ Could not post payment '%s': %s", payment.name, str(e))
                
                # NOTE: Payment reconciliation is SKIPPED to keep payment_state as "not_paid"
                # Payments are created and posted, but NOT reconciled with the bill
                # This ensures payment_status remains "not_paid" as per requirement
                # Payments can be manually reconciled later if needed
                _logger.info("📋 Payment '%s' created and posted for bill '%s' (NOT reconciled to keep payment_state as 'not_paid')", 
                           payment.name, bill.name)
                
                created_payments.append(payment.id)
                
            except Exception as e:
                _logger.error("❌ Error migrating payment: %s", str(e), exc_info=True)
                continue
        
        _logger.info("✅ Migrated %s/%s payment(s) for bill %s", len(created_payments), len(payments_odoo14), bill.name)
        return created_payments
    
    def action_migrate(self):
        """Migrate this vendor bill from Odoo 14 to Odoo 19"""
        self.ensure_one()
        
        if self.status not in ('pending_migration', 'queued'):
            raise UserError('Can only migrate vendor bills with "Pending Migration" or "Queued" status')
        
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
            
            # Get initial bill data from Odoo 14
            safe_initial_fields = ['id', 'name']
            bills = []
            
            try:
                bills = client.search_read(
                    'account.move',
                    [('name', '=', self.uploaded_bill_number), ('move_type', '=', 'in_invoice')],
                    safe_initial_fields,
                    limit=1
                )
            except Exception as e:
                _logger.debug("Error fetching vendor bill: %s", str(e))
            
            if not bills:
                self.write({
                    'status': 'not_found',
                    'status_message': 'Vendor bill not found in Odoo 14',
                })
                return
            
            bill_data = bills[0]
            
            # Check if bill already exists in Odoo 19 BEFORE migrating
            existing_bill = self.env['account.move'].search([
                ('name', '=', self.uploaded_bill_number),
                ('move_type', '=', 'in_invoice')
            ], limit=1)
            
            if existing_bill:
                _logger.info("Vendor bill %s already exists in Odoo 19 (ID: %s), marking as migrated", 
                           self.uploaded_bill_number, existing_bill.id)
                self.write({
                    'status': 'migrated',
                    'status_message': 'Already migrated (existed in system)',
                    'odoo19_bill_id': existing_bill.id,
                    'in_system_bill_number': existing_bill.name,
                    'migration_date': fields.Datetime.now(),
                    'error_message': False,
                })
                self.env.cr.commit()
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'vendor.bill.migration.line',
                    'view_mode': 'list,form',
                    'target': 'current',
                }
            
            # Update status to migrating with retry on serialization errors
            def _update_status_migrating():
                self.write({
                    'status': 'migrating',
                    'status_message': 'Migration in progress...',
                })
                self.env.cr.commit()
            
            try:
                _retry_on_serialization_error(_update_status_migrating)
            except Exception as e:
                error_msg = str(e)
                _logger.error("Failed to update status to migrating after retries: %s", error_msg)
                # Try to refresh and check if already migrating
                self.invalidate_recordset(['status'])
                if self.status == 'migrating':
                    _logger.info("Record %s is already in migrating status, skipping", self.uploaded_bill_number)
                    raise UserError('This vendor bill is already being migrated by another process')
                raise
            
            # Get fields to fetch - dynamically check which fields exist
            excluded_fields = ['display_name', 'name_get', 'name_search']
            
            # Standard fields for account.move (vendor bill)
            fields_to_fetch = [
                'id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due', 'state', 'payment_state',
                'amount_total', 'amount_untaxed', 'amount_tax', 'currency_id', 'journal_id', 'ref', 'narration',
                'invoice_origin', 'invoice_payment_term_id', 'fiscal_position_id', 'purchase_id', 'user_id',
                'invoice_line_ids', 'line_ids', 'company_id', 'branch_id',  # branch_id from Odoo 14 maps to company in Odoo 19
                'create_date', 'write_date', 'write_uid', 'create_uid',
                # Custom fields from metro_erp (Odoo 14)
                'location', 'site_name', 'create_do', 'picking_ids', 'is_wo_header', 'bank_details',
                'file_to_upload', 'filename', 'is_with_stamp', 'voucher_no', 'in_note', 'lpo_n', 
                'quote_reference', 'po_no',
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
                full_bill = client.search_read(
                    'account.move',
                    [('id', '=', bill_data['id'])],
                    fields_to_fetch,
                    limit=1
                )
            except Exception as e:
                _logger.warning("Error fetching vendor bill with expanded fields: %s. Using minimal safe fields.", str(e))
                full_bill = client.search_read(
                    'account.move',
                    [('id', '=', bill_data['id'])],
                    minimal_safe_fields,
                    limit=1
                )
            
            if not full_bill:
                raise UserError('Could not fetch full vendor bill data')
            
            bill_data = full_bill[0]
            
            # Prepare bill values for Odoo 19
            bill_vals = {
                'move_type': 'in_invoice',  # Vendor bill
            }
            
            # Map name (bill number) - REQUIRED
            if bill_data.get('name'):
                bill_vals['name'] = bill_data['name']
            else:
                bill_vals['name'] = self.uploaded_bill_number
            
            # Map partner_id (required field)
            if bill_data.get('partner_id'):
                partner_id = bill_data['partner_id']
                partner_name = False
                
                if isinstance(partner_id, (list, tuple)) and len(partner_id) > 1:
                    partner_name = partner_id[1]
                    partner_id = partner_id[0]
                elif isinstance(partner_id, (list, tuple)) and len(partner_id) > 0:
                    partner_id = partner_id[0]
                
                # Priority 1: Search by exact name if we have it
                partner = False
                if partner_name:
                    partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
                
                # Priority 2: Fallback to ID search (risky, as IDs might not match between dbs)
                if not partner:
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
                    bill_vals['partner_id'] = partner.id
                else:
                    raise UserError('Could not find or create partner for vendor bill')
            else:
                raise UserError('Partner is required for vendor bill')
            
            # Map company_id - Priority: Excel company name > Odoo 14 branch_id (via mapping) > Odoo 14 company_id
            company = False
            
            # Priority 1: Try to find company from Excel company field
            if self.company:
                company = self.env['res.company'].search([
                    ('name', 'ilike', self.company)
                ], limit=1)
                if company:
                    _logger.info("✅ Found company '%s' (ID: %s) from Excel field for vendor bill %s", 
                               company.name, company.id, self.uploaded_bill_number)
            
            # Priority 2: Try Odoo 14 branch_id (map to Odoo 19 company via branch_company_mapping)
            if not company:
                branch_id = bill_data.get('branch_id')
                branch_name = None
                _logger.info("🔍 Checking branch_id from Odoo 14: %s (type: %s)", branch_id, type(branch_id).__name__)
                
                if branch_id:
                    if isinstance(branch_id, (list, tuple)) and len(branch_id) > 0:
                        # Many2one format: [id, name]
                        if len(branch_id) > 1:
                            branch_id_value = branch_id[0]
                            branch_name = branch_id[1]  # Extract branch name
                            _logger.info("   Extracted branch_id: %s, branch_name: %s", branch_id_value, branch_name)
                        else:
                            branch_id_value = branch_id[0]
                            _logger.info("   Extracted branch_id: %s", branch_id_value)
                        branch_id = branch_id_value
                    
                    # Fetch branch name from Odoo 14 if not already extracted
                    if not branch_name and branch_id:
                        try:
                            branch_data = client.search_read(
                                'res.branch',  # Assuming branch model name in Odoo 14
                                [('id', '=', branch_id)],
                                ['name'],
                                limit=1
                            )
                            if branch_data:
                                branch_name = branch_data[0].get('name')
                                _logger.info("   Fetched branch_name from Odoo 14: %s", branch_name)
                        except Exception as branch_fetch_error:
                            _logger.debug("   Could not fetch branch name from Odoo 14 (model might be different): %s", str(branch_fetch_error))
                            # Try alternative model names
                            for model_name in ['account.branch', 'branch.branch', 'res.company.branch']:
                                try:
                                    branch_data = client.search_read(
                                        model_name,
                                        [('id', '=', branch_id)],
                                        ['name'],
                                        limit=1
                                    )
                                    if branch_data:
                                        branch_name = branch_data[0].get('name')
                                        _logger.info("   Fetched branch_name from Odoo 14 (%s): %s", model_name, branch_name)
                                        break
                                except:
                                    continue
                    
                    # Use branch_company_mapping to get Odoo 19 company
                    try:
                        mapping_model = self.env['odoo14.branch.company.mapping']
                        if not mapping_model:
                            _logger.warning("⚠️ branch_company_mapping model not found in registry")
                        else:
                            # Try mapping by branch_id first
                            company = mapping_model.get_company_for_branch(odoo14_branch_id=branch_id, odoo14_branch_name=None)
                            if company:
                                _logger.info("✅ Found company '%s' (ID: %s) from Odoo 14 branch_id %s via mapping for vendor bill %s", 
                                           company.name, company.id, branch_id, self.uploaded_bill_number)
                            elif branch_name:
                                # If branch_id mapping failed, try by branch_name
                                _logger.info("🔍 Branch ID mapping not found, trying branch name mapping: %s", branch_name)
                                company = mapping_model.get_company_for_branch(odoo14_branch_id=None, odoo14_branch_name=branch_name)
                                if company:
                                    _logger.info("✅ Found company '%s' (ID: %s) from Odoo 14 branch_name '%s' via mapping for vendor bill %s", 
                                               company.name, company.id, branch_name, self.uploaded_bill_number)
                    except Exception as mapping_error:
                        _logger.warning("⚠️ Could not map branch_id %s or branch_name '%s' to company via mapping table: %s", 
                                      branch_id, branch_name or 'N/A', str(mapping_error), exc_info=True)
                    
                    # If mapping table didn't find a match, try direct name matching (Odoo 14 branch name = Odoo 19 company name)
                    if not company and branch_name:
                        _logger.info("🔍 Mapping table didn't find a match, trying direct name match: branch_name '%s' = company name", branch_name)
                        company = self.env['res.company'].search([
                            ('name', '=', branch_name)  # Exact match first
                        ], limit=1)
                        if not company:
                            # Try case-insensitive match
                            company = self.env['res.company'].search([
                                ('name', 'ilike', branch_name)
                            ], limit=1)
                        if company:
                            _logger.info("✅ Found company '%s' (ID: %s) by direct name match with Odoo 14 branch_name '%s' for vendor bill %s", 
                                       company.name, company.id, branch_name, self.uploaded_bill_number)
                        else:
                            _logger.warning("⚠️ No company found with name matching Odoo 14 branch_name '%s'", branch_name)
                            _logger.warning("   Please create a mapping in: Accounting > Configuration > Odoo 14 Branch Company Mapping")
                    elif not company and branch_id:
                        _logger.warning("⚠️ No company mapping found for branch_id %s and branch_name not available", branch_id)
                        _logger.warning("   Please create a mapping in: Accounting > Configuration > Odoo 14 Branch Company Mapping")
                else:
                    _logger.info("   No branch_id found in bill_data")
            
            # Priority 3: Try Odoo 14 company_id if Excel company and branch_id not found
            if not company:
                company_id = bill_data.get('company_id')
                if company_id:
                    if isinstance(company_id, (list, tuple)) and len(company_id) > 0:
                        company_id = company_id[0]
                    company = self.env['res.company'].search([('id', '=', company_id)], limit=1)
                    if company:
                        _logger.info("✅ Found company '%s' (ID: %s) from Odoo 14 company_id for vendor bill %s", 
                                   company.name, company.id, self.uploaded_bill_number)
            
            # Fallback to default company
            if not company:
                company = self.env.company
                _logger.warning("⚠️ Company not found from Excel ('%s'), branch_id, or Odoo 14 company_id, using default company: %s", 
                              self.company or 'N/A', company.name)
            
            bill_vals['company_id'] = company.id
            
            # Map invoice_date
            if bill_data.get('invoice_date'):
                bill_vals['invoice_date'] = bill_data['invoice_date']
            elif self.invoice_bill_date:
                bill_vals['invoice_date'] = self.invoice_bill_date
            else:
                bill_vals['invoice_date'] = fields.Date.today()
            
            # Map invoice_date_due
            if bill_data.get('invoice_date_due'):
                bill_vals['invoice_date_due'] = bill_data['invoice_date_due']
            elif self.due_date:
                bill_vals['invoice_date_due'] = self.due_date
            
            # Map currency_id - Always use AED for vendor bill migration
            original_currency = None
            if bill_data.get('currency_id'):
                currency_id = bill_data['currency_id']
                if isinstance(currency_id, (list, tuple)) and len(currency_id) > 0:
                    currency_id = currency_id[0]
                original_currency = self.env['res.currency'].search([('id', '=', currency_id)], limit=1)
                if original_currency:
                    _logger.info("📊 Original currency from Odoo 14: %s (ID: %s), but using AED for migration", 
                               original_currency.name, original_currency.id)
            
            # Always use AED for vendor bill migration
            aed_currency = self.env['res.currency'].search([
                '|',
                ('name', '=', 'AED'),
                ('symbol', '=', 'AED')
            ], limit=1)
            
            if aed_currency:
                bill_vals['currency_id'] = aed_currency.id
                _logger.info("✅ Using AED currency (ID: %s) for vendor bill %s", aed_currency.id, self.uploaded_bill_number)
            else:
                # Fallback to company currency if AED not found
                bill_vals['currency_id'] = company.currency_id.id
                _logger.warning("⚠️ AED currency not found, using company currency: %s", company.currency_id.name)
            
            # Map journal_id - CRITICAL: Must belong to the same company
            if bill_data.get('journal_id'):
                journal_id = bill_data['journal_id']
                if isinstance(journal_id, (list, tuple)) and len(journal_id) > 0:
                    journal_id = journal_id[0]
                # Search by ID AND company_id to ensure company match
                journal = self.env['account.journal'].search([
                    ('id', '=', journal_id),
                    ('type', '=', 'purchase'),
                    ('company_id', '=', bill_vals['company_id'])  # CRITICAL: Must match bill's company
                ], limit=1)
                if journal:
                    bill_vals['journal_id'] = journal.id
                    _logger.info("✅ Found journal '%s' (ID: %s) for company '%s'", journal.name, journal.id, company.name)
                else:
                    # Journal not found or company mismatch - find default purchase journal for company
                    _logger.warning("⚠️ Journal ID %s not found or company mismatch, finding default purchase journal for company '%s'", 
                                  journal_id, company.name)
                    journal = self.env['account.journal'].search([
                        ('type', '=', 'purchase'),
                        ('company_id', '=', bill_vals['company_id'])
                    ], limit=1)
                    if journal:
                        bill_vals['journal_id'] = journal.id
                        _logger.info("✅ Using default purchase journal '%s' (ID: %s) for company '%s'", journal.name, journal.id, company.name)
                    else:
                        # Last resort: Try to find ANY purchase journal in 'Metro Fire' branch
                        _logger.warning("⚠️ No purchase journal found for company '%s', trying fallback to 'Metro Fire'...", company.name)
                        metro_fire = self.env['res.company'].search([('name', '=', 'Metro Fire')], limit=1)
                        if metro_fire:
                            journal = self.env['account.journal'].search([
                                ('type', '=', 'purchase'),
                                ('company_id', '=', metro_fire.id)
                            ], limit=1)
                            if journal:
                                bill_vals['journal_id'] = journal.id
                                _logger.info("✅ Using fallback journal '%s' (ID: %s) from company 'Metro Fire' for bill company '%s'", journal.name, journal.id, company.name)
                            else:
                                error_msg = f"No purchase journal found for bill company '{company.name}' and no purchase journal found for fallback company 'Metro Fire'. Please create one."
                                _logger.error("❌ %s", error_msg)
                                raise UserError(error_msg)
                        else:
                            error_msg = f"No purchase journal found for bill company '{company.name}' and fallback company 'Metro Fire' not found in Odoo 19."
                            _logger.error("❌ %s", error_msg)
                            raise UserError(error_msg)
            else:
                # Find default purchase journal for company
                journal = self.env['account.journal'].search([
                    ('type', '=', 'purchase'),
                    ('company_id', '=', bill_vals['company_id'])
                ], limit=1)
                if journal:
                    bill_vals['journal_id'] = journal.id
                    _logger.info("✅ Using default purchase journal '%s' (ID: %s) for company '%s'", journal.name, journal.id, company.name)
                else:
                    # Last resort: Try to find ANY purchase journal in 'Metro Fire' branch
                    _logger.warning("⚠️ No purchase journal found for company '%s', trying fallback to 'Metro Fire'...", company.name)
                    metro_fire = self.env['res.company'].search([('name', '=', 'Metro Fire')], limit=1)
                    if metro_fire:
                        journal = self.env['account.journal'].search([
                            ('type', '=', 'purchase'),
                            ('company_id', '=', metro_fire.id)
                        ], limit=1)
                        if journal:
                            bill_vals['journal_id'] = journal.id
                            _logger.info("✅ Using fallback journal '%s' (ID: %s) from company 'Metro Fire' for bill company '%s'", journal.name, journal.id, company.name)
                        else:
                            error_msg = f"No purchase journal found for bill company '{company.name}' and no purchase journal found for fallback company 'Metro Fire'. Please create one."
                            _logger.error("❌ %s", error_msg)
                            raise UserError(error_msg)
                    else:
                        error_msg = f"No purchase journal found for bill company '{company.name}' and fallback company 'Metro Fire' not found in Odoo 19."
                        _logger.error("❌ %s", error_msg)
                        raise UserError(error_msg)
            
            # Store state from Excel (priority) or Odoo 14, payment_state always "not_paid"
            # Priority: Excel status > Odoo 14 state
            odoo14_state_value = bill_data.get('state', 'draft')
            excel_state_value = self.excel_status or ''
            
            # Determine state: Excel status takes priority
            if excel_state_value:
                excel_state_lower = str(excel_state_value).lower()
                if 'posted' in excel_state_lower or 'post' in excel_state_lower:
                    final_state = 'posted'
                else:
                    final_state = 'draft'
            else:
                final_state = odoo14_state_value
            
            # Payment state is always "not_paid"
            odoo14_payment_state_value = 'not_paid'
            
            # Update migration line with state and payment_state with retry
            def _update_state_fields():
                self.write({
                    'odoo14_state': final_state,
                    'odoo14_payment_state': odoo14_payment_state_value,
                })
                self.env.cr.commit()
            
            try:
                _retry_on_serialization_error(_update_state_fields)
            except Exception as e:
                _logger.warning("Failed to update state fields after retries (non-critical): %s", str(e))
                # Non-critical, continue migration
            
            _logger.info("📋 Vendor bill %s - State: %s (from Excel: %s, Odoo 14: %s), Payment State: %s", 
                        self.uploaded_bill_number, final_state, excel_state_value or 'N/A', odoo14_state_value, odoo14_payment_state_value)
            
            # Store state for later posting (don't set it during creation)
            should_post = False
            bill_state = 'draft'
            
            # Priority 1: Check Excel status first
            if self.excel_status:
                excel_status_lower = str(self.excel_status).lower()
                if 'posted' in excel_status_lower or 'post' in excel_status_lower:
                    should_post = True
                    bill_state = 'posted'
                    _logger.info("📋 Vendor bill %s has 'Posted' status in Excel - will post after creation", self.uploaded_bill_number)
            
            # Priority 2: Check Odoo 14 state if Excel status not available or not posted
            if not should_post and bill_data.get('state'):
                bill_state = bill_data['state']
                if bill_state == 'posted':
                    should_post = True
                    _logger.info("📋 Vendor bill %s was in 'posted' state in Odoo 14 - will post after creation", self.uploaded_bill_number)
            
            # Map ref
            if bill_data.get('ref'):
                bill_vals['ref'] = bill_data['ref']
            
            # Map narration
            if bill_data.get('narration'):
                bill_vals['narration'] = bill_data['narration']
            
            # Map invoice_origin (for linking to purchase order)
            if bill_data.get('invoice_origin'):
                bill_vals['invoice_origin'] = bill_data['invoice_origin']
            
            # Map invoice_payment_term_id - ensure company matches
            if bill_data.get('invoice_payment_term_id'):
                payment_term_id = bill_data['invoice_payment_term_id']
                if isinstance(payment_term_id, (list, tuple)) and len(payment_term_id) > 0:
                    payment_term_id = payment_term_id[0]
                payment_term = self.env['account.payment.term'].search([
                    ('id', '=', payment_term_id),
                    '|',
                    ('company_id', '=', False),  # Global payment terms
                    ('company_id', '=', company.id)  # Company-specific payment terms
                ], limit=1)
                if payment_term:
                    bill_vals['invoice_payment_term_id'] = payment_term.id
                else:
                    _logger.warning("Payment term %s not found or company mismatch for bill %s, skipping", 
                                  payment_term_id, self.uploaded_bill_number)
            
            # Map fiscal_position_id - CRITICAL: Must be global or belong to the same company
            if bill_data.get('fiscal_position_id'):
                fiscal_position_id = bill_data['fiscal_position_id']
                if isinstance(fiscal_position_id, (list, tuple)) and len(fiscal_position_id) > 0:
                    fiscal_position_id = fiscal_position_id[0]
                # Search for fiscal position: global (company_id=False) OR company-specific matching bill's company
                fiscal_position = self.env['account.fiscal.position'].search([
                    ('id', '=', fiscal_position_id),
                    '|',
                    ('company_id', '=', False),  # Global fiscal positions (allowed)
                    ('company_id', '=', company.id)  # Company-specific fiscal positions (must match)
                ], limit=1)
                if fiscal_position:
                    # Double-check: if fiscal position has a company, it must match
                    if fiscal_position.company_id and fiscal_position.company_id.id != company.id:
                        _logger.warning("⚠️ Fiscal position '%s' (ID: %s) belongs to company '%s', but bill belongs to '%s' - skipping", 
                                      fiscal_position.name, fiscal_position.id, fiscal_position.company_id.name, company.name)
                    else:
                        bill_vals['fiscal_position_id'] = fiscal_position.id
                        if fiscal_position.company_id:
                            _logger.info("✅ Found fiscal position '%s' (ID: %s) for company '%s'", 
                                       fiscal_position.name, fiscal_position.id, company.name)
                        else:
                            _logger.info("✅ Found global fiscal position '%s' (ID: %s)", fiscal_position.name, fiscal_position.id)
                else:
                    _logger.warning("⚠️ Fiscal position ID %s not found or company mismatch for bill %s (company: %s), skipping", 
                                  fiscal_position_id, self.uploaded_bill_number, company.name)
            
            # Map custom fields from eq_fc_purchase_custom (Odoo 19)
            # quote_reference (Char in Odoo 19, Many2one in Odoo 14)
            if bill_data.get('quote_reference'):
                quote_ref = bill_data['quote_reference']
                if isinstance(quote_ref, (list, tuple)) and len(quote_ref) > 1:
                    # Many2one returns [id, name]
                    bill_vals['quote_reference'] = quote_ref[1]  # Use name
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
                            bill_vals['quote_reference'] = quote_data[0].get('name', '')
                    except:
                        pass
                else:
                    bill_vals['quote_reference'] = str(quote_ref)
            elif self.quote_reference:
                bill_vals['quote_reference'] = self.quote_reference
            
            # lpo_number (from lpo_n in Odoo 14)
            if bill_data.get('lpo_n'):
                bill_vals['lpo_number'] = bill_data['lpo_n']
            elif self.lpo_number:
                bill_vals['lpo_number'] = self.lpo_number
            
            # voucher_number (from voucher_no in Odoo 14)
            if bill_data.get('voucher_no'):
                bill_vals['voucher_number'] = bill_data['voucher_no']
            elif self.voucher_number:
                bill_vals['voucher_number'] = self.voucher_number
            
            # po_number
            if bill_data.get('po_no'):
                bill_vals['po_number'] = bill_data['po_no']
            elif self.po_number:
                bill_vals['po_number'] = self.po_number
            
            # is_wo_header
            if bill_data.get('is_wo_header'):
                bill_vals['is_wo_header'] = bill_data['is_wo_header']
            
            # is_with_stamp
            if bill_data.get('is_with_stamp'):
                bill_vals['is_with_stamp'] = bill_data['is_with_stamp']
            
            # Map custom fields from eq_fc_invoice_custom (available on all account.move including vendor bills)
            # location
            if bill_data.get('location'):
                bill_vals['location'] = bill_data['location']
            
            # site_name
            if bill_data.get('site_name'):
                bill_vals['site_name'] = bill_data['site_name']
            
            # create_do
            if bill_data.get('create_do'):
                bill_vals['create_do'] = bill_data['create_do']
            
            # bank_details
            if bill_data.get('bank_details'):
                bill_vals['bank_details'] = bill_data['bank_details']
            
            # file_to_upload and filename
            if bill_data.get('file_to_upload'):
                bill_vals['file_to_upload'] = bill_data['file_to_upload']
            if bill_data.get('filename'):
                bill_vals['filename'] = bill_data['filename']
            
            # in_note
            if bill_data.get('in_note'):
                bill_vals['in_note'] = bill_data['in_note']
            
            # Link to purchase order if available - ensure company matches
            purchase_order = False
            if bill_data.get('purchase_id'):
                purchase_id = bill_data['purchase_id']
                if isinstance(purchase_id, (list, tuple)) and len(purchase_id) > 0:
                    purchase_id = purchase_id[0]
                purchase_order = self.env['purchase.order'].search([('id', '=', purchase_id)], limit=1)
                if purchase_order:
                    # Verify purchase order company matches bill company
                    if purchase_order.company_id.id != company.id:
                        _logger.warning("Purchase order %s has different company (%s) than bill (%s), skipping purchase_id", 
                                      purchase_order.name, purchase_order.company_id.name, company.name)
                        purchase_order = False
                    else:
                        bill_vals['purchase_id'] = purchase_order.id
            elif bill_vals.get('invoice_origin'):
                # Try to find purchase order by invoice_origin
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', bill_vals['invoice_origin'])
                ], limit=1)
                if purchase_order:
                    # Verify purchase order company matches bill company
                    if purchase_order.company_id.id != company.id:
                        _logger.warning("Purchase order %s has different company (%s) than bill (%s), skipping purchase_id", 
                                      purchase_order.name, purchase_order.company_id.name, company.name)
                        purchase_order = False
                    else:
                        bill_vals['purchase_id'] = purchase_order.id
            
            # Map user_id (responsible user)
            if bill_data.get('user_id'):
                user_id = bill_data['user_id']
                if isinstance(user_id, (list, tuple)) and len(user_id) > 0:
                    user_id = user_id[0]
                user = self.env['res.users'].search([('id', '=', user_id)], limit=1)
                if user:
                    bill_vals['user_id'] = user.id
                    _logger.info("✅ Mapped user_id: %s (ID: %s)", user.name, user.id)
                else:
                    _logger.warning("⚠️ User ID %s not found in Odoo 19, skipping user_id", user_id)
            
            # Create vendor bill in Odoo 19 (always in draft state)
            if 'state' in bill_vals:
                del bill_vals['state']
            
            # Validate company consistency for bill fields before creation
            bill_company_id = bill_vals.get('company_id')
            if bill_company_id:
                # Validate journal company
                if bill_vals.get('journal_id'):
                    journal = self.env['account.journal'].browse(bill_vals['journal_id'])
                    if journal.company_id.id != bill_company_id:
                        _logger.warning("Journal %s has different company (%s) than bill (%s), finding replacement", 
                                      journal.name, journal.company_id.name, company.name)
                        replacement_journal = self.env['account.journal'].search([
                            ('type', '=', 'purchase'),
                            ('company_id', '=', bill_company_id)
                        ], limit=1)
                        if replacement_journal:
                            bill_vals['journal_id'] = replacement_journal.id
                        else:
                            _logger.error("No replacement journal found, removing journal_id")
                            del bill_vals['journal_id']
                
                # Validate fiscal_position_id company
                if bill_vals.get('fiscal_position_id'):
                    fiscal_position = self.env['account.fiscal.position'].browse(bill_vals['fiscal_position_id'])
                    # Fiscal position must be global (company_id=False) OR belong to bill's company
                    if fiscal_position.company_id and fiscal_position.company_id.id != bill_company_id:
                        _logger.warning("⚠️ Fiscal position '%s' (ID: %s) has different company (%s) than bill (%s), removing", 
                                      fiscal_position.name, fiscal_position.id, fiscal_position.company_id.name, company.name)
                        del bill_vals['fiscal_position_id']
                    else:
                        _logger.debug("✅ Fiscal position '%s' validated (global or company match)", fiscal_position.name)
                
                # Validate partner company (if partner has company_id)
                if bill_vals.get('partner_id'):
                    partner = self.env['res.partner'].browse(bill_vals['partner_id'])
                    if hasattr(partner, 'company_id') and partner.company_id and partner.company_id.id != bill_company_id:
                        _logger.warning("Partner %s has different company (%s) than bill (%s), but continuing", 
                                      partner.name, partner.company_id.name, company.name)
                        # Partners can be shared, so we continue
            
            # Create bill with company context to ensure proper validation
            try:
                bill = self.env['account.move'].with_company(company.id).create(bill_vals)
                _logger.info("✅ Created vendor bill %s in draft state (ID: %s)", bill.name, bill.id)
            except Exception as bill_error:
                error_msg = str(bill_error)
                if 'company inconsistencies' in error_msg.lower() or 'uh-oh' in error_msg.lower():
                    _logger.error("❌ Company inconsistency error creating bill %s: %s", self.uploaded_bill_number, error_msg)
                    _logger.error("   Bill company: %s (ID: %s)", company.name, company.id)
                    _logger.error("   Bill values: journal_id=%s, partner_id=%s, purchase_id=%s", 
                                bill_vals.get('journal_id'), bill_vals.get('partner_id'), bill_vals.get('purchase_id'))
                    # Try without purchase_id if it exists
                    if bill_vals.get('purchase_id'):
                        _logger.warning("⚠️ Retrying bill creation without purchase_id")
                        bill_vals_no_po = bill_vals.copy()
                        del bill_vals_no_po['purchase_id']
                        bill = self.env['account.move'].with_company(company.id).create(bill_vals_no_po)
                        _logger.info("✅ Created vendor bill %s without purchase_id (ID: %s)", bill.name, bill.id)
                    else:
                        raise
                else:
                    raise
            
            # Preserve original creation date and user
            src_create_date = bill_data.get('create_date')
            src_write_date = bill_data.get('write_date')
            src_create_uid = bill_data.get('create_uid')
            src_write_uid = bill_data.get('write_uid')
            
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
                        user = self.env['res.users'].search([('id', '=', src_create_uid)], limit=1)
                        if not user:
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
                    params.append(bill.id)
                    
                    self.env.cr.execute(update_sql, params)
                except Exception as e:
                    _logger.warning("Could not set original dates/users: %s", str(e))
            
            # Migrate bill lines - Fetch lines directly with filtering to avoid description lines
            # DON'T trust invoice_line_ids - fetch lines directly and filter by product_id
            line_ids_to_migrate = []
            
            try:
                _logger.info("🔄 Fetching invoice lines directly from Odoo 14 for bill %s...", self.uploaded_bill_number)
                # Fetch all lines for this bill
                all_lines = client.search_read(
                    'account.move.line',
                    [('move_id', '=', bill_data['id'])],
                    ['id', 'product_id', 'name', 'quantity', 'price_unit', 'display_type', 'tax_line_id'],
                    limit=200
                )
                
                if all_lines:
                    _logger.info("📋 Fetched %s total lines from Odoo 14 for bill %s", len(all_lines), self.uploaded_bill_number)
                    
                    # Filter lines: ONLY include lines with product_id AND quantity > 0 AND price_unit > 0
                    # Also track product+qty+price combinations to detect duplicates
                    seen_combinations = {}  # Key: (product_id, quantity, price_unit) -> line_id
                    
                    for line in all_lines:
                        line_id = line.get('id')
                        if not line_id:
                            continue
                        
                        # Skip tax lines
                        if line.get('tax_line_id'):
                            _logger.debug("   Skipping line %s (tax line)", line_id)
                            continue
                        
                        # Skip section/note lines
                        display_type = line.get('display_type')
                        if display_type and display_type in ('line_section', 'line_note'):
                            _logger.debug("   Skipping line %s (display_type='%s')", line_id, display_type)
                            continue
                        
                        # Check for product_id - MUST be a valid positive integer
                        product_id = line.get('product_id')
                        product_id_valid = False
                        
                        if product_id:
                            if isinstance(product_id, (list, tuple)) and len(product_id) > 0:
                                # Many2one format: [id, name]
                                extracted_id = product_id[0]
                                if isinstance(extracted_id, int) and extracted_id > 0:
                                    product_id = extracted_id
                                    product_id_valid = True
                            elif isinstance(product_id, int) and product_id > 0:
                                product_id_valid = True
                        
                        # CRITICAL: Only proceed if we have a valid positive product_id
                        if not product_id_valid or not product_id or product_id <= 0:
                            _logger.debug("   Skipping line %s (no valid product_id: %s) - name: '%s'", 
                                        line_id, product_id, (line.get('name', '') or 'N/A')[:50])
                            continue
                        
                        # Check quantity and price - round to 2 decimal places to avoid floating point precision issues
                        quantity = line.get('quantity', 0.0) or 0.0
                        price_unit = line.get('price_unit', 0.0) or 0.0
                        
                        # Round to 2 decimal places for comparison (standard currency precision)
                        quantity = round(float(quantity), 2)
                        price_unit = round(float(price_unit), 2)
                        
                        if quantity <= 0.0 or price_unit <= 0.0:
                            _logger.debug("   Skipping line %s (quantity=%s or price=%s is zero) - name: '%s'", 
                                        line_id, quantity, price_unit, (line.get('name', '') or 'N/A')[:50])
                            continue
                        
                        # CRITICAL: Check for duplicate lines using product_id + quantity + price
                        # This prevents migrating the same line multiple times if fetched twice
                        combo_key = (product_id, quantity, price_unit)
                        if combo_key in seen_combinations:
                            # This is an exact duplicate (same product, qty, and price) - skip it
                            existing_line_id = seen_combinations[combo_key]
                            _logger.warning("⏭️ Skipping duplicate line %s (same product_id=%s, qty=%s, price=%s as line %s) - keeping first occurrence only", 
                                          line_id, product_id, quantity, price_unit, existing_line_id)
                            continue
                        
                        # First occurrence of this combination - keep it
                        seen_combinations[combo_key] = line_id
                        line_ids_to_migrate.append(line_id)
                        _logger.debug("   ✅ Including line %s (product_id=%s, qty=%s, price=%s)", 
                                    line_id, product_id, quantity, price_unit)
                    
                    if len(all_lines) != len(line_ids_to_migrate):
                        skipped_count = len(all_lines) - len(line_ids_to_migrate)
                        _logger.info("✅ Filtered %s lines: %s valid product lines, %s skipped (tax/note/duplicate/zero qty/price)", 
                                    len(all_lines), len(line_ids_to_migrate), skipped_count)
                    
                    # FINAL CHECK: Ensure no duplicate line IDs (shouldn't happen, but double-check)
                    original_line_ids = line_ids_to_migrate
                    line_ids_to_migrate = list(dict.fromkeys(line_ids_to_migrate))  # Preserves order, removes duplicates
                    if len(original_line_ids) != len(line_ids_to_migrate):
                        _logger.error("❌ CRITICAL: Found %s duplicate line IDs in line_ids_to_migrate after deduplication! This should NOT happen!", 
                                    len(original_line_ids) - len(line_ids_to_migrate))
                        _logger.error("   Original: %s", original_line_ids)
                        _logger.error("   Deduplicated: %s", line_ids_to_migrate)
                    
                    _logger.info("✅ Filtered to %s unique product lines (deduplicated by product_id+qty+price) for bill %s", 
                                len(line_ids_to_migrate), self.uploaded_bill_number)
                    _logger.info("   Line IDs: %s", line_ids_to_migrate)
                    
                    # Log all seen combinations for debugging
                    if seen_combinations:
                        _logger.info("   Seen combinations (product_id, qty, price) -> line_id: %s", 
                                    {f"({k[0]}, {k[1]}, {k[2]})": v for k, v in seen_combinations.items()})
                else:
                    _logger.error("❌ No lines found in Odoo 14 for bill %s", self.uploaded_bill_number)
            except Exception as fetch_error:
                _logger.error("❌ Error fetching lines from Odoo 14: %s", str(fetch_error), exc_info=True)
            
            # Fallback: If direct fetch failed, try invoice_line_ids (but with heavy filtering)
            if not line_ids_to_migrate:
                _logger.error("❌ CRITICAL: No invoice line IDs found for bill %s", self.uploaded_bill_number)
                _logger.error("   invoice_line_ids from Odoo 14: %s (type: %s)", 
                            bill_data.get('invoice_line_ids', 'Not found'), 
                            type(bill_data.get('invoice_line_ids')).__name__)
                _logger.error("   line_ids from Odoo 14: %s (type: %s)", 
                            bill_data.get('line_ids', 'Not found'),
                            type(bill_data.get('line_ids')).__name__)
                
                # Try to fetch lines directly using get_invoice_lines method
                try:
                    _logger.info("🔄 Attempting to fetch lines directly using get_invoice_lines method...")
                    direct_lines = client.get_invoice_lines(bill_data['id'])
                    if direct_lines:
                        fallback_ids = []
                        for line in direct_lines:
                            if line.get('id'):
                                fallback_ids.append(line['id'])
                        # CRITICAL: Deduplicate immediately using set()
                        fallback_ids_unique = list(set(fallback_ids))
                        if len(fallback_ids) != len(fallback_ids_unique):
                            _logger.error("❌ Found %s duplicate line IDs in get_invoice_lines! Removing duplicates.", 
                                        len(fallback_ids) - len(fallback_ids_unique))
                        line_ids_to_migrate = fallback_ids_unique
                        _logger.info("✅ Found %s unique line IDs via get_invoice_lines method", len(line_ids_to_migrate))
                    else:
                        _logger.error("❌ get_invoice_lines returned empty list for bill %s", self.uploaded_bill_number)
                except Exception as direct_fetch_error:
                    _logger.error("❌ Could not fetch lines directly: %s", str(direct_fetch_error), exc_info=True)
                
                # Final attempt: Try to search for lines by move_id
                if not line_ids_to_migrate:
                    try:
                        _logger.info("🔄 Final attempt: Searching for lines by move_id in Odoo 14...")
                        all_lines = client.search_read(
                            'account.move.line',
                            [('move_id', '=', bill_data['id']), ('display_type', '=', False)],
                            ['id'],
                            limit=100
                        )
                        if all_lines:
                            search_ids = []
                            for line in all_lines:
                                if line.get('id'):
                                    search_ids.append(line['id'])
                            # CRITICAL: Deduplicate immediately using set()
                            search_ids_unique = list(set(search_ids))
                            if len(search_ids) != len(search_ids_unique):
                                _logger.error("❌ Found %s duplicate line IDs in search! Removing duplicates.", 
                                            len(search_ids) - len(search_ids_unique))
                            line_ids_to_migrate = search_ids_unique
                            _logger.info("✅ Found %s unique line IDs by searching move_id", len(line_ids_to_migrate))
                    except Exception as search_error:
                        _logger.error("❌ Could not search for lines: %s", str(search_error), exc_info=True)
            
            if line_ids_to_migrate:
                # FINAL VERIFICATION: Ensure NO duplicates before processing
                final_unique_count = len(set(line_ids_to_migrate))
                if len(line_ids_to_migrate) != final_unique_count:
                    _logger.error("❌ CRITICAL ERROR: line_ids_to_migrate contains %s duplicates! Forcing deduplication.", 
                                 len(line_ids_to_migrate) - final_unique_count)
                    _logger.error("   Original list: %s", line_ids_to_migrate)
                    line_ids_to_migrate = list(set(line_ids_to_migrate))
                    _logger.error("   Deduplicated list: %s", line_ids_to_migrate)
                
                try:
                    total_lines = len(line_ids_to_migrate)
                    successful_lines = 0
                    failed_lines = 0
                    
                    _logger.info("🔒 FINAL VERIFICATION: Processing %s UNIQUE line IDs: %s", total_lines, line_ids_to_migrate)
                    
                    # Update total_items_odoo14 before starting migration
                    try:
                        # Check if transaction is aborted before writing
                        try:
                            self.env.cr.execute("SELECT 1")
                        except Exception as check_error:
                            if 'current transaction is aborted' in str(check_error).lower():
                                _logger.warning("⚠️ Transaction aborted, rolling back before updating total_items_odoo14...")
                                self.env.cr.rollback()
                        
                        self.write({
                            'total_items_odoo14': total_lines,
                        })
                        self.env.cr.commit()
                    except Exception as update_error:
                        error_msg = str(update_error).lower()
                        if 'current transaction is aborted' in error_msg:
                            try:
                                self.env.cr.rollback()
                                _logger.warning("⚠️ Rolled back transaction, retrying total_items_odoo14 update...")
                                # Retry after rollback
                                self.write({
                                    'total_items_odoo14': total_lines,
                                })
                                self.env.cr.commit()
                            except:
                                _logger.warning("⚠️ Could not update total_items_odoo14, continuing anyway")
                        else:
                            _logger.warning("⚠️ Could not update total_items_odoo14: %s", str(update_error))
                    
                    _logger.info("=" * 80)
                    _logger.info("📋 STARTING LINE MIGRATION: %s lines to migrate for bill %s", total_lines, self.uploaded_bill_number)
                    _logger.info("   Bill ID in Odoo 19: %s", bill.id)
                    _logger.info("   Bill Company: %s (ID: %s)", bill.company_id.name, bill.company_id.id)
                    _logger.info("=" * 80)
                    
                    # Track processed line IDs to prevent duplicates during processing
                    processed_line_ids = set()  # Track line IDs to prevent processing same line twice
                    
                    for line_idx, line_id in enumerate(line_ids_to_migrate):
                        # CRITICAL: Skip if we've already processed this line ID
                        if line_id in processed_line_ids:
                            _logger.warning("⚠️ Skipping duplicate line ID %s (already processed in this migration)", line_id)
                            failed_lines += 1
                            continue
                        processed_line_ids.add(line_id)
                        
                        # Periodic status update for long-running migrations (every 10 lines)
                        if line_idx > 0 and line_idx % 10 == 0:
                            try:
                                self.write({
                                    'status_message': f'Migrating lines... {line_idx}/{total_lines}',
                                })
                                self.env.cr.commit()
                            except:
                                pass  # Non-critical, continue migration
                        try:
                            line_data = client.search_read(
                                'account.move.line',
                                [('id', '=', line_id), ('move_id', '=', bill_data['id'])],
                                ['product_id', 'name', 'quantity', 'price_unit', 'discount', 'tax_ids', 
                                 'account_id', 'sequence', 'purchase_line_id', 'brand_id', 'company_id', 'display_type',
                                 'tax_line_id', 'tax_base_amount'],  # Add tax_line_id to identify tax lines
                                limit=1
                            )
                            if line_data and len(line_data) > 0:
                                line_info = line_data[0]
                                # Skip section/note lines - only migrate product lines
                                # Only skip if display_type is explicitly set to 'line_section' or 'line_note'
                                display_type = line_info.get('display_type')
                                if display_type and display_type in ('line_section', 'line_note'):
                                    _logger.info("⏭️ Skipping line %s (display_type='%s' - section/note line)", 
                                               line_id, display_type)
                                    failed_lines += 1
                                    continue
                                
                                # CRITICAL: Filter out tax lines and system-generated lines FIRST
                                # Tax lines have tax_line_id set
                                is_tax_line = bool(line_info.get('tax_line_id'))
                                
                                # Skip tax lines
                                if is_tax_line:
                                    _logger.info("⏭️ Skipping line %s (tax line - tax_line_id=%s)", 
                                               line_id, line_info.get('tax_line_id'))
                                    failed_lines += 1
                                    continue
                                
                                # CRITICAL: Extract and validate product_id - MUST be a valid positive integer
                                product_id_raw = line_info.get('product_id')
                                product_id_valid = False
                                product_id_value = None
                                
                                if product_id_raw:
                                    if isinstance(product_id_raw, (list, tuple)) and len(product_id_raw) > 0:
                                        # Many2one format: [id, name]
                                        extracted_id = product_id_raw[0]
                                        if isinstance(extracted_id, int) and extracted_id > 0:
                                            product_id_value = extracted_id
                                            product_id_valid = True
                                    elif isinstance(product_id_raw, int) and product_id_raw > 0:
                                        product_id_value = product_id_raw
                                        product_id_valid = True
                                
                                # CRITICAL: ONLY migrate lines that have a VALID product_id (positive integer)
                                # Skip ALL lines without valid product_id (descriptions, notes, system lines, etc.)
                                if not product_id_valid or not product_id_value:
                                    _logger.info("⏭️ Skipping line %s (no valid product_id: %s) - description/note/system line", 
                                               line_id, product_id_raw)
                                    _logger.info("   Line name: '%s'", (line_info.get('name', '') or 'N/A')[:100])
                                    failed_lines += 1
                                    continue
                                
                                # CRITICAL: Skip lines with zero quantity or zero price FIRST
                                # Real product lines should have quantity > 0 and price_unit > 0
                                # This ensures we prioritize actual product lines over description lines
                                line_quantity = line_info.get('quantity', 0.0) or 0.0
                                line_price = line_info.get('price_unit', 0.0) or 0.0
                                
                                if line_quantity <= 0.0 or line_price <= 0.0:
                                    _logger.info("⏭️ Skipping line %s (quantity=%s or price=%s is zero - likely description/duplicate line)", 
                                                line_id, line_quantity, line_price)
                                    _logger.info("   Line name: '%s'", (line_info.get('name', '') or 'N/A')[:100])
                                    failed_lines += 1
                                    continue
                                
                                # No longer checking processed_product_ids here, as we already deduplicate by (product, qty, price) earlier.
                                
                                # Extract account_id
                                has_account = False
                                account_id_raw = line_info.get('account_id')
                                if account_id_raw:
                                    if isinstance(account_id_raw, (list, tuple)) and len(account_id_raw) > 0:
                                        has_account = bool(account_id_raw[0])
                                    elif isinstance(account_id_raw, int):
                                        has_account = bool(account_id_raw)
                                
                                # Skip lines without account (invalid lines)
                                if not has_account:
                                    _logger.warning("⚠️ Line %s has product_id but no account_id, skipping", line_id)
                                    failed_lines += 1
                                    continue
                                
                                
                                
                                # Use the validated product_id_value for logging and mapping
                                product_id_from_odoo14 = product_id_value
                                
                                _logger.info("📋 Fetched line %s/%s data: name='%s', qty=%s, price=%s, product_id=%s, account_id=%s", 
                                            line_idx + 1, total_lines,
                                            (line_info.get('name', '') or 'Line')[:50], 
                                            line_info.get('quantity', 1.0),
                                            line_info.get('price_unit', 0.0),
                                            product_id_from_odoo14 or 'None',
                                            line_info.get('account_id'))
                            else:
                                _logger.warning("⚠️ Line %s not found in Odoo 14 for bill %s, skipping", line_id, bill_data.get('name', 'N/A'))
                                failed_lines += 1
                                continue
                            
                            # line_info is already set above, create line_vals
                            # CRITICAL: For vendor bills, we need to create invoice lines (not tax/payment lines)
                            # In Odoo 19, invoice lines are determined by display_type=None/empty and having product/account
                            line_vals = {
                                'move_id': bill.id,
                                'company_id': bill.company_id.id,  # Required: must match bill's company
                                'name': line_info.get('name', '') or 'Line',
                                'quantity': line_info.get('quantity', 1.0) or 1.0,
                                'price_unit': line_info.get('price_unit', 0.0) or 0.0,
                                'discount': line_info.get('discount', 0.0) or 0.0,
                                # Do NOT set display_type - leave it as None for regular product lines
                                # display_type is only set for section/note lines ('line_section', 'line_note')
                            }
                            
                            _logger.info("📝 Preparing line %s/%s: name='%s', qty=%s, price=%s", 
                                       line_idx + 1, total_lines,
                                       (line_info.get('name', '') or 'Line')[:50],
                                       line_info.get('quantity', 1.0),
                                       line_info.get('price_unit', 0.0))
                            
                            if line_info.get('sequence'):
                                line_vals['sequence'] = line_info['sequence']
                            
                            # Map product_id - ALWAYS find or create product
                            product = False
                            if line_info.get('product_id'):
                                product_id = line_info['product_id']
                                product_name = False
                                
                                if isinstance(product_id, (list, tuple)) and len(product_id) > 1:
                                    product_name = product_id[1]
                                    product_id = product_id[0]
                                elif isinstance(product_id, (list, tuple)) and len(product_id) > 0:
                                    product_id = product_id[0]
                                
                                # Step 1: Priority search by exact name if we have it
                                if product_name:
                                    product = self.env['product.product'].search([('name', '=', product_name)], limit=1)
                                
                                # Step 2: Try to find by ID (fallback, as IDs might not match between databases)
                                if not product:
                                    product = self.env['product.product'].search([('id', '=', product_id)], limit=1)
                                
                                # Step 3: If not found by name or ID, fetch details from Odoo 14 and search by code/barcode
                                if not product:
                                    try:
                                        _logger.info("🔍 Product '%s' (ID %s) not found in Odoo 19, fetching details from Odoo 14...", product_name or 'Unknown', product_id)
                                        product_data = client.search_read(
                                            'product.product',
                                            [('id', '=', product_id)],
                                            ['name', 'default_code', 'barcode', 'categ_id', 'uom_id', 'type', 
                                             'sale_ok', 'purchase_ok', 'standard_price', 'list_price'],
                                            limit=1
                                        )
                                        if product_data:
                                            prod_data = product_data[0]
                                            
                                            # Try to find by default_code (most reliable)
                                            if prod_data.get('default_code'):
                                                product = self.env['product.product'].search([
                                                    ('default_code', '=', prod_data['default_code'])
                                                ], limit=1)
                                                if product:
                                                    _logger.info("✅ Found product by default_code: %s (ID: %s)", 
                                                               product.default_code, product.id)
                                            
                                            # Try to find by name from Odoo 14 if original name wasn't provided directly
                                            if not product and prod_data.get('name'):
                                                product = self.env['product.product'].search([
                                                    ('name', '=', prod_data['name'])
                                                ], limit=1)
                                                if product:
                                                    _logger.info("✅ Found product by name: %s (ID: %s)", 
                                                               product.name, product.id)
                                            
                                            # Try to find by barcode if not found
                                            if not product and prod_data.get('barcode'):
                                                product = self.env['product.product'].search([
                                                    ('barcode', '=', prod_data['barcode'])
                                                ], limit=1)
                                                if product:
                                                    _logger.info("✅ Found product by barcode: %s (ID: %s)", 
                                                               product.barcode, product.id)
                                        else:
                                            # Fallback: Odoo 14 returned no data for this product ID
                                            _logger.warning("⚠️ Could not fetch details for Product ID %s from Odoo 14. Using fallback creation.", product_id)
                                            product_name_fallback = product_name or "Unknown Product"
                                            
                                            # Try to find by name one last time

                                            product = self.env['product.product'].search([
                                                ('name', '=', product_name_fallback)
                                            ], limit=1)
                                            
                                            if not product:
                                                try:
                                                    _logger.info("📦 Creating fallback product: '%s'", product_name_fallback)
                                                    product = self.env['product.product'].create({
                                                        'name': product_name_fallback,
                                                        'default_code': f"MIGRATED-MISSING-{product_id}",
                                                        'type': 'consu',
                                                        'purchase_ok': True,
                                                    })
                                                    _logger.info("✅ Created fallback product (ID: %s)", product.id)
                                                except Exception as fallback_create_error:
                                                    _logger.error("❌ Failed to create fallback product: %s", str(fallback_create_error))

                                        # Use standard creation flow if we found data but no product yet (and it wasn't the fallback case above)
                                        if product_data and not product:
                                            
                                            # Step 3: If still not found, CREATE the product
                                            if not product:
                                                _logger.info("📦 Creating new product in Odoo 19: %s", prod_data.get('name', 'N/A'))
                                                product_vals = {
                                                    'name': prod_data.get('name', 'Migrated Product'),
                                                    'type': prod_data.get('type', 'consu'),
                                                    'sale_ok': prod_data.get('sale_ok', False),
                                                    'purchase_ok': prod_data.get('purchase_ok', True),
                                                }
                                                
                                                if prod_data.get('default_code'):
                                                    product_vals['default_code'] = prod_data['default_code']
                                                
                                                if prod_data.get('barcode'):
                                                    product_vals['barcode'] = prod_data['barcode']
                                                
                                                # Map category if available
                                                if prod_data.get('categ_id'):
                                                    categ_id = prod_data['categ_id']
                                                    if isinstance(categ_id, (list, tuple)) and len(categ_id) > 0:
                                                        categ_id = categ_id[0]
                                                    category = self.env['product.category'].search([('id', '=', categ_id)], limit=1)
                                                    if not category:
                                                        # Try to find by name
                                                        try:
                                                            categ_data = client.search_read(
                                                                'product.category',
                                                                [('id', '=', categ_id)],
                                                                ['name'],
                                                                limit=1
                                                            )
                                                            if categ_data:
                                                                category = self.env['product.category'].search([
                                                                    ('name', '=', categ_data[0].get('name'))
                                                                ], limit=1)
                                                        except:
                                                            pass
                                                    if category:
                                                        product_vals['categ_id'] = category.id
                                                
                                                # Map UoM if available
                                                if prod_data.get('uom_id'):
                                                    uom_id = prod_data['uom_id']
                                                    if isinstance(uom_id, (list, tuple)) and len(uom_id) > 0:
                                                        uom_id = uom_id[0]
                                                    uom = self.env['uom.uom'].search([('id', '=', uom_id)], limit=1)
                                                    if uom:
                                                        product_vals['uom_id'] = uom.id
                                                    else:
                                                        # Default to Units
                                                        product_vals['uom_id'] = self.env.ref('uom.product_uom_unit', raise_if_not_found=False).id or False
                                                
                                                # Set purchase UoM same as UoM
                                                if product_vals.get('uom_id'):
                                                    product_vals['uom_po_id'] = product_vals['uom_id']
                                                
                                                try:
                                                    product = self.env['product.product'].create(product_vals)
                                                    _logger.info("✅ Created product '%s' (ID: %s, Code: %s) in Odoo 19", 
                                                               product.name, product.id, product.default_code or 'N/A')
                                                except Exception as create_error:
                                                    _logger.error("❌ Failed to create product: %s", str(create_error), exc_info=True)
                                                    # Try with minimal fields
                                                    try:
                                                        minimal_product_vals = {
                                                            'name': prod_data.get('name', 'Migrated Product'),
                                                            'type': 'consu',
                                                        }
                                                        if prod_data.get('default_code'):
                                                            minimal_product_vals['default_code'] = prod_data['default_code']
                                                        product = self.env['product.product'].create(minimal_product_vals)
                                                        _logger.info("✅ Created product with minimal fields: %s (ID: %s)", 
                                                                   product.name, product.id)
                                                    except Exception as minimal_error:
                                                        _logger.error("❌ Failed to create product even with minimal fields: %s", str(minimal_error))
                                    except Exception as product_error:
                                        _logger.error("❌ Error fetching/creating product: %s", str(product_error), exc_info=True)
                                
                                # Verify product company if it has company_id field (products are usually global, but check anyway)
                                if product and hasattr(product, 'company_id') and product.company_id:
                                    if product.company_id.id != bill.company_id.id:
                                        _logger.warning("⚠️ Product %s has different company (%s) than bill (%s), but continuing (products can be shared)", 
                                                      product.name, product.company_id.name, bill.company_id.name)
                                        # Products can be shared across companies, so we continue
                                
                                if product:
                                    line_vals['product_id'] = product.id
                                    _logger.info("✅ Product mapped for line %s: %s (ID: %s, Code: %s)", 
                                               line_id, product.name, product.id, product.default_code or 'N/A')
                                    _logger.info("   ✅ product_id=%s will be set in line_vals", product.id)
                                else:
                                    _logger.warning("⚠️ Could not find or create product for line %s (Odoo 14 product_id: %s), line will be created without product", 
                                                  line_id, product_id if 'product_id' in locals() else 'N/A')
                            
                            # Map account_id (required field) - PRIORITY: Always use 501100 PURCHASE EXPENSES for vendor bills
                            account = False
                            
                            # PRIORITY 1: Always use 501100 PURCHASE EXPENSES for vendor bill lines (if it exists)
                            purchase_expense_account = _search_account_safe(
                                self.env,
                                [('code', '=', '501100')],
                                company_id=bill.company_id.id,
                                limit=1
                            )
                            
                            if purchase_expense_account:
                                account = purchase_expense_account
                                _logger.info("✅ Using 501100 PURCHASE EXPENSES account for vendor bill line: %s (ID: %s)", 
                                           account.name, account.id)
                            else:
                                # If 501100 doesn't exist, log warning and fall back to other methods
                                _logger.warning("⚠️ 501100 PURCHASE EXPENSES account not found for company '%s', falling back to other account matching methods", 
                                              bill.company_id.name)
                                
                                # Fallback: Try to match by Odoo 14 account code
                                account_code_from_odoo14 = None
                                
                                if line_info.get('account_id'):
                                    account_id = line_info['account_id']
                                    if isinstance(account_id, (list, tuple)) and len(account_id) > 0:
                                        account_id = account_id[0]
                                    
                                    # Fetch account code from Odoo 14
                                    try:
                                        account_data = client.search_read(
                                            'account.account',
                                            [('id', '=', account_id)],
                                            ['name', 'code', 'account_type', 'internal_group'],
                                            limit=1
                                        )
                                        if account_data:
                                            acc_data = account_data[0]
                                            account_code_from_odoo14 = acc_data.get('code')
                                            _logger.info("📋 Fetched account from Odoo 14: Code='%s', Name='%s'", 
                                                       account_code_from_odoo14, acc_data.get('name', 'N/A'))
                                    except Exception as account_fetch_error:
                                        _logger.warning("⚠️ Could not fetch account from Odoo 14: %s", str(account_fetch_error))
                                    
                                    # Try to find by code in bill's company
                                    if account_code_from_odoo14:
                                        account = _search_account_safe(
                                            self.env,
                                            [('code', '=', account_code_from_odoo14)],
                                            company_id=bill.company_id.id,
                                            limit=1
                                        )
                                        
                                        if account:
                                            _logger.info("✅ Found account by code '%s' in company '%s': %s (ID: %s)", 
                                                       account_code_from_odoo14, bill.company_id.name, account.name, account.id)
                                
                                # Fallback: Try product's expense account (only if company matches)
                                if not account and line_vals.get('product_id'):
                                    product = self.env['product.product'].browse(line_vals['product_id'])
                                    if product.property_account_expense_id:
                                        account_company_id = getattr(product.property_account_expense_id, 'company_id', False)
                                        if account_company_id and account_company_id.id == bill.company_id.id:
                                            account = product.property_account_expense_id
                                            _logger.info("✅ Using product's expense account: %s (Code: %s, ID: %s)", 
                                                       account.name, account.code, account.id)
                                
                                # Final fallback: Find default expense account for the company
                                if not account:
                                    default_account = _search_account_safe(
                                        self.env,
                                        [('internal_group', '=', 'expense')],
                                        company_id=bill.company_id.id,
                                        limit=1,
                                        order='code asc'
                                    )
                                    if default_account:
                                        account = default_account
                                        _logger.info("✅ Using default expense account: %s (Code: %s, ID: %s)", 
                                                   account.name, account.code, account.id)
                            
                            if account:
                                # Verify account company matches bill company
                                # Check if account has company_id attribute (Odoo 19 accounts always have company_id)
                                account_company_id = getattr(account, 'company_id', False)
                                if account_company_id and account_company_id.id != bill.company_id.id:
                                    _logger.warning("Account %s has different company (%s) than bill (%s), finding replacement", 
                                                  account.code, account_company_id.name, bill.company_id.name)
                                    # Find replacement account in bill's company
                                    replacement_account = _search_account_safe(
                                        self.env,
                                        [('code', '=', account.code)],
                                        company_id=bill.company_id.id,
                                        limit=1
                                    )
                                    if replacement_account:
                                        account = replacement_account
                                    else:
                                        # Use default expense account for company
                                        account = _search_account_safe(
                                            self.env,
                                            [('internal_group', '=', 'expense')],
                                            company_id=bill.company_id.id,
                                            limit=1,
                                            order='code asc'
                                        )
                                        if not account:
                                            _logger.error("Could not find replacement account for line %s, skipping account_id", line_id)
                                            account = False
                                if account:
                                    line_vals['account_id'] = account.id
                                    _logger.info("✅ Set account_id for line %s: %s (Code: %s)", 
                                               line_id, account.name, account.code)
                            
                            # CRITICAL: If account_id is still not set, find a default account
                            if not line_vals.get('account_id'):
                                # Account is REQUIRED - PRIORITY: Always use 501100 PURCHASE EXPENSES for vendor bills
                                _logger.warning("⚠️ Account not set for vendor bill line %s, using 501100 PURCHASE EXPENSES", line_id)
                                
                                # Priority 1: Try 501100 PURCHASE EXPENSES (REQUIRED for vendor bills)
                                default_account = _search_account_safe(
                                    self.env,
                                    [('code', '=', '501100')],
                                    company_id=bill.company_id.id,
                                    limit=1
                                )
                                
                                if default_account:
                                    line_vals['account_id'] = default_account.id
                                    _logger.info("✅ Using 501100 PURCHASE EXPENSES account for line %s: %s (ID: %s)", 
                                               line_id, default_account.name, default_account.id)
                                else:
                                    # Priority 2: Any expense account (fallback if 501100 doesn't exist)
                                    _logger.warning("⚠️ 501100 PURCHASE EXPENSES not found, using fallback expense account")
                                    default_account = _search_account_safe(
                                        self.env,
                                        [('internal_group', '=', 'expense')],
                                        company_id=bill.company_id.id,
                                        limit=1,
                                        order='code asc'
                                    )
                                    
                                    # Priority 3: Journal's default account
                                    if not default_account:
                                        if bill.journal_id and bill.journal_id.default_account_id:
                                            default_account = bill.journal_id.default_account_id
                                    
                                    if default_account:
                                        line_vals['account_id'] = default_account.id
                                        _logger.info("✅ Using fallback account for line %s: %s (Code: %s)", 
                                                   line_id, default_account.name, default_account.code)
                                    else:
                                        _logger.error("❌ CRITICAL: No account found for line %s - line cannot be created without account_id", line_id)
                                        raise UserError(f'Cannot create vendor bill line without account_id. Bill: {bill.name}, Line: {line_id}')
                            
                            # Map tax_ids - Use Company Default Purchase Tax
                            # FIX 2024-01-06: User requested to ALWAYS use the Default Purchase Tax of the company
                            # "product tax, should be default Purchase Tax of the company , don't change other"
                            taxes = self.env['account.tax']
                            
                            # For product lines, apply the Company's Default Purchase Tax
                            if line_vals.get('product_id'):
                                if bill.company_id.account_purchase_tax_id:
                                    taxes = bill.company_id.account_purchase_tax_id
                                    _logger.info("✅ Applied Company Default Purchase Tax '%s' (ID: %s) to line %s", 
                                               taxes.name, taxes.id, line_id)
                                else:
                                    _logger.warning("⚠️ No Default Purchase Tax configured for company '%s'", bill.company_id.name)
                            
                            if taxes:
                                line_vals['tax_ids'] = [(6, 0, taxes.ids)]
                            
                            # Priority 2: If no tax from line, check product's default purchase tax in Odoo 14
                            if not taxes and line_vals.get('product_id'):
                                try:
                                    product_id_odoo14 = line_info.get('product_id')
                                    if isinstance(product_id_odoo14, (list, tuple)) and len(product_id_odoo14) > 0:
                                        product_id_odoo14 = product_id_odoo14[0]
                                    
                                    if product_id_odoo14:
                                        _logger.info("🔍 Line %s has no tax, checking product's default purchase tax in Odoo 14 (product_id: %s)...", 
                                                   line_id, product_id_odoo14)
                                        # Fetch product's purchase tax from Odoo 14
                                        product_data = client.search_read(
                                            'product.product',
                                            [('id', '=', product_id_odoo14)],
                                            ['supplier_taxes_id', 'name'],
                                            limit=1
                                        )
                                        
                                        if product_data and product_data[0].get('supplier_taxes_id'):
                                            supplier_tax_ids = product_data[0]['supplier_taxes_id']
                                            if isinstance(supplier_tax_ids, (list, tuple)):
                                                extracted_supplier_tax_ids = []
                                                for tid in supplier_tax_ids:
                                                    if isinstance(tid, int):
                                                        extracted_supplier_tax_ids.append(tid)
                                                    elif isinstance(tid, (list, tuple)) and len(tid) > 0:
                                                        extracted_supplier_tax_ids.append(tid[0])
                                                
                                                if extracted_supplier_tax_ids:
                                                    # Fetch tax details from Odoo 14
                                                    tax_data_list = client.search_read(
                                                        'account.tax',
                                                        [('id', 'in', extracted_supplier_tax_ids)],
                                                        ['name', 'amount', 'type_tax_use', 'amount_type'],
                                                        limit=10
                                                    )
                                                    
                                                    for tax_data in tax_data_list:
                                                        tax_name = tax_data.get('name', '')
                                                        tax_amount = tax_data.get('amount', 0.0)
                                                        tax_type = tax_data.get('type_tax_use', 'none')
                                                        
                                                        # Search for matching tax in Odoo 19 by name and amount
                                                        matching_tax = self.env['account.tax'].search([
                                                            ('company_id', '=', bill.company_id.id),
                                                            ('name', 'ilike', tax_name),
                                                            ('amount', '=', tax_amount),
                                                            ('type_tax_use', '=', tax_type)
                                                        ], limit=1)
                                                        
                                                        if matching_tax and matching_tax not in taxes:
                                                            taxes |= matching_tax
                                                            _logger.info("✅ Found product's default purchase tax '%s' (ID: %s) from Odoo 14 for line %s", 
                                                                       matching_tax.name, matching_tax.id, line_id)
                                except Exception as product_tax_error:
                                    _logger.debug("Could not fetch product's purchase tax from Odoo 14: %s", str(product_tax_error))
                            
                            # Priority 3: If still no tax, use default purchase VAT tax for the company
                            if not taxes:
                                _logger.info("🔍 Line %s has no tax from line or product, trying default purchase VAT tax for company '%s'...", 
                                           line_id, bill.company_id.name)
                                # Try to find default purchase VAT tax (type_tax_use='purchase', typically VAT 5%)
                                default_purchase_tax = self.env['account.tax'].search([
                                    ('company_id', '=', bill.company_id.id),
                                    ('type_tax_use', '=', 'purchase'),
                                    ('amount', '>', 0)  # Only taxes with amount > 0
                                ], limit=1, order='amount desc')  # Prefer higher VAT rates first
                                
                                if default_purchase_tax:
                                    taxes = default_purchase_tax
                                    _logger.info("✅ Using default purchase VAT tax '%s' (ID: %s, Amount: %s%%) for line %s", 
                                               default_purchase_tax.name, default_purchase_tax.id, default_purchase_tax.amount, line_id)
                                else:
                                    _logger.warning("⚠️ No default purchase VAT tax found for company '%s', line %s will have no tax", 
                                                  bill.company_id.name, line_id)
                            
                            # Set tax_ids if we found any taxes
                            if taxes:
                                line_vals['tax_ids'] = [(6, 0, taxes.ids)]
                                _logger.info("✅ Mapped %s tax(es) to line %s: %s", len(taxes), line_id, ', '.join(taxes.mapped('name')))
                            else:
                                # CRITICAL: Always try to get default purchase VAT tax as absolute last resort
                                _logger.warning("⚠️ No taxes found for line %s (tried line tax, product tax), trying default purchase VAT one more time...", line_id)
                                default_purchase_tax = self.env['account.tax'].search([
                                    ('company_id', '=', bill.company_id.id),
                                    ('type_tax_use', '=', 'purchase'),
                                    ('amount', '>', 0)
                                ], limit=1, order='amount desc')
                                if default_purchase_tax:
                                    taxes = default_purchase_tax
                                    line_vals['tax_ids'] = [(6, 0, [default_purchase_tax.id])]
                                    _logger.info("✅ Using default purchase VAT tax '%s' (ID: %s, Amount: %s%%) for line %s", 
                                               default_purchase_tax.name, default_purchase_tax.id, default_purchase_tax.amount, line_id)
                                else:
                                    _logger.warning("⚠️ No default purchase VAT tax found for company '%s', line %s will have no tax", 
                                                  bill.company_id.name, line_id)
                            
                            # Map purchase_line_id for linking to purchase order lines
                            if line_info.get('purchase_line_id') and bill_vals.get('purchase_id'):
                                purchase_line_id = line_info['purchase_line_id']
                                if isinstance(purchase_line_id, (list, tuple)) and len(purchase_line_id) > 0:
                                    purchase_line_id = purchase_line_id[0]
                                if purchase_line_id and purchase_order:
                                    # Ensure purchase order has same company
                                    if purchase_order.company_id.id != bill.company_id.id:
                                        _logger.warning("Purchase order %s has different company (%s) than bill (%s), skipping purchase_line_id", 
                                                      purchase_order.name, purchase_order.company_id.name, bill.company_id.name)
                                    else:
                                        purchase_line = self.env['purchase.order.line'].search([
                                            ('id', '=', purchase_line_id),
                                            ('order_id', '=', purchase_order.id)
                                        ], limit=1)
                                        if purchase_line:
                                            line_vals['purchase_line_id'] = purchase_line.id
                            
                            # Map brand_id (custom field)
                            if line_info.get('brand_id'):
                                brand_id = line_info['brand_id']
                                if isinstance(brand_id, (list, tuple)) and len(brand_id) > 0:
                                    brand_id = brand_id[0]
                                brand = self.env['product.brand'].search([('id', '=', brand_id)], limit=1)
                                if brand:
                                    line_vals['brand_id'] = brand.id
                            
                            # CRITICAL: Ensure account_id is ALWAYS set before validation
                            if not line_vals.get('account_id'):
                                _logger.error("❌ CRITICAL: account_id is missing for line %s, attempting to set...", line_id)
                                # Try to get account one more time
                                if not account:
                                    # PRIORITY: Force use of 501100 PURCHASE EXPENSES
                                    account = _search_account_safe(
                                        self.env,
                                        [('code', '=', '501100')],
                                        company_id=bill.company_id.id,
                                        limit=1
                                    )
                                    
                                    if account:
                                        _logger.info("✅ Set account_id for line %s to 501100 PURCHASE EXPENSES: %s (ID: %s)", 
                                                   line_id, account.name, account.id)
                                    else:
                                        # Fallback: Use default expense account
                                        account = _search_account_safe(
                                            self.env,
                                            [('internal_group', '=', 'expense')],
                                            company_id=bill.company_id.id,
                                            limit=1,
                                            order='code asc'
                                        )
                                        
                                        if account:
                                            _logger.info("✅ Set account_id for line %s to default expense account: %s (Code: %s)", 
                                                       line_id, account.name, account.code)
                                        else:
                                            raise UserError(f'Cannot create vendor bill line {line_id} - no account available. Bill: {bill.name}')
                                
                                if account:
                                    line_vals['account_id'] = account.id
                            
                            # Validate company consistency before creating line
                            # Check all Many2one fields for company compatibility
                            validation_errors = []
                            
                            if line_vals.get('account_id'):
                                account = self.env['account.account'].browse(line_vals['account_id'])
                                account_company_id = getattr(account, 'company_id', False)
                                if account_company_id and account_company_id.id != bill.company_id.id:
                                    validation_errors.append(f"Account {account.code} (company: {account_company_id.name})")
                            
                            if line_vals.get('product_id'):
                                product = self.env['product.product'].browse(line_vals['product_id'])
                                if hasattr(product, 'company_id') and product.company_id and product.company_id.id != bill.company_id.id:
                                    validation_errors.append(f"Product {product.name} (company: {product.company_id.name})")
                            
                            if line_vals.get('tax_ids'):
                                tax_ids = line_vals['tax_ids'][0][2] if line_vals['tax_ids'] else []
                                if tax_ids:
                                    taxes = self.env['account.tax'].browse(tax_ids)
                                    for tax in taxes:
                                        if tax.company_id.id != bill.company_id.id:
                                            validation_errors.append(f"Tax {tax.name} (company: {tax.company_id.name})")
                            
                            if validation_errors:
                                error_msg = f"Company inconsistencies detected for line {line_id}: {', '.join(validation_errors)}. Bill company: {bill.company_id.name}"
                                _logger.error("❌ %s", error_msg)
                                # Try to fix by removing problematic fields
                                if line_vals.get('tax_ids'):
                                    # Re-filter taxes to only include matching company
                                    tax_ids = line_vals['tax_ids'][0][2] if line_vals['tax_ids'] else []
                                    if tax_ids:
                                        valid_taxes = self.env['account.tax'].search([
                                            ('id', 'in', tax_ids),
                                            ('company_id', '=', bill.company_id.id)
                                        ])
                                        if valid_taxes:
                                            line_vals['tax_ids'] = [(6, 0, valid_taxes.ids)]
                                        else:
                                            del line_vals['tax_ids']
                                
                                # Ensure account is correct
                                if line_vals.get('account_id'):
                                    account = self.env['account.account'].browse(line_vals['account_id'])
                                    account_company_id = getattr(account, 'company_id', False)
                                    if account_company_id and account_company_id.id != bill.company_id.id:
                                        # Find replacement account
                                        replacement_account = _search_account_safe(
                                            self.env,
                                            [('code', '=', account.code)],
                                            company_id=bill.company_id.id,
                                            limit=1
                                        )
                                        if replacement_account:
                                            line_vals['account_id'] = replacement_account.id
                                        else:
                                            # Use default expense account
                                            default_account = _search_account_safe(
                                                self.env,
                                                [('internal_group', '=', 'expense')],
                                                company_id=bill.company_id.id,
                                                limit=1,
                                                order='code asc'
                                            )
                                            if default_account:
                                                line_vals['account_id'] = default_account.id
                                            else:
                                                _logger.error("No valid account found for line %s, removing account_id", line_id)
                                                del line_vals['account_id']
                            
                            # Ensure company_id is always set
                            line_vals['company_id'] = bill.company_id.id
                            
                            # CRITICAL: Verify account_id is set before creating line
                            if not line_vals.get('account_id'):
                                _logger.error("❌ CRITICAL ERROR: account_id is missing for line %s before creation!", line_id)
                                _logger.error("   Line values: %s", line_vals)
                                raise UserError(f'Cannot create vendor bill line {line_id} - account_id is missing. Bill: {bill.name}')
                            
                            # Try to create the line with full data (using company context)
                            creation_success = False
                            created_line = None
                            
                            try:
                                with self.env.cr.savepoint():
                                    _logger.info("🔄 Creating line %s/%s (Odoo 14 ID: %s)", 
                                               line_idx + 1, total_lines, line_id)
                                    _logger.info("   Line values: move_id=%s, name='%s', qty=%s, price=%s", 
                                               line_vals.get('move_id'), line_vals.get('name', '')[:30], 
                                               line_vals.get('quantity'), line_vals.get('price_unit'))
                                    
                                    # CRITICAL: Ensure bill is in draft state before creating lines
                                    if bill.state != 'draft':
                                        _logger.warning("⚠️ Bill %s is not in draft state (%s), resetting to draft before creating lines", 
                                                      bill.name, bill.state)
                                        bill.button_draft()
                                        bill.invalidate_recordset(['state'])
                                        bill = self.env['account.move'].browse(bill.id)
                                    
                                    # CRITICAL: Create the line using the bill's context with sudo() for permissions
                                    created_line = self.env['account.move.line'].with_company(bill.company_id.id).sudo().create(line_vals)
                                    
                                    # Verify creation succeeded
                                    if created_line and created_line.id:
                                        creation_success = True
                            except Exception as create_exception:
                                _logger.error("❌ CRITICAL: Failed to create line %s/%s: %s", 
                                            line_idx + 1, total_lines, str(create_exception))
                                # We intentionally swallow the exception here to let the fallback logic handle it
                                # BUT only if creation_success is False
                            
                            # POST-CREATION ACTIONS (Only if creation succeeded)
                            if creation_success and created_line:
                                try:
                                    # Verify product is set on the line
                                    product_info = "No Product"
                                    if created_line.product_id:
                                        product_info = f"Product: {created_line.product_id.name} (ID: {created_line.product_id.id})"
                                    
                                    _logger.info("✅ SUCCESS: Created vendor bill line %s/%s (Odoo 19 ID: %s, Odoo 14 ID: %s)", 
                                               line_idx + 1, total_lines, created_line.id, line_id)
                                    _logger.info("   %s", product_info)
                                    
                                    # Verify the line is actually linked to the bill
                                    if created_line.move_id.id != bill.id:
                                        _logger.error("❌ CRITICAL: Created line %s is not linked to bill %s!", created_line.id, bill.id)
                                    
                                    # Commit after each successful line creation
                                    self.env.cr.commit()
                                    successful_lines += 1
                                    
                                    # Compute taxes (safe to fail)
                                    try:
                                        created_line._compute_tax_amount()
                                        created_line._compute_price_subtotal()
                                    except:
                                        pass
                                except Exception as post_create_error:
                                    _logger.warning("⚠️ Error during post-creation checks for line %s (line was created successfully): %s", 
                                                  created_line.id, str(post_create_error))
                                    # Do NOT re-raise to avoid triggering fallback (which would create a duplicate)
                            
                            # FALLBACK LOGIC (Only if creation FAILED)
                            elif not creation_success:
                                _logger.warning("⚠️ Primary line creation failed for line %s, attempting fallback strategies...", line_id)
                                
                                # CRITICAL: STRICT PRODUCT CHECK
                                # If the original line had a product, but we are here, it means we likely failed to map it
                                # or failed to create the line with it.
                                # OLD BEHAVIOR: Created a description-only line (bad)
                                # NEW BEHAVIOR: Skip the line if product is missing but required
                                if product_id_from_odoo14 and not line_vals.get('product_id'):
                                    _logger.error("❌ STRICT MODE: Skipping line %s because it had a product in Odoo 14 (ID: %s) but product mapping failed.", 
                                                 line_id, product_id_from_odoo14)
                                    _logger.error("   We will NOT create a description-only line to prevent data corruption.")
                                    failed_lines += 1
                                    continue

                                try:
                                    # Try validation error fix (Company inconsistencies)
                                    # Try to create with minimal required fields only
                                    _logger.warning("⚠️ Attempting to create line %s with minimal fields", line_id)
                                    
                                    minimal_line_vals = {
                                        'move_id': bill.id,
                                        'company_id': bill.company_id.id,
                                        'name': line_vals.get('name', 'Line'),
                                        'quantity': line_vals.get('quantity', 1.0),
                                        'price_unit': line_vals.get('price_unit', 0.0),
                                        'discount': line_vals.get('discount', 0.0),
                                    }
                                    
                                    # Add product if we have it (preserving strictness)
                                    if line_vals.get('product_id'):
                                        minimal_line_vals['product_id'] = line_vals['product_id']
                                    elif product_id_from_odoo14:
                                         # Should be caught by strict check above, but double check
                                         _logger.error("❌ Aborting minimal creation: Product required but missing.")
                                         failed_lines += 1
                                         continue

                                    # Fix account inconsistencies
                                    if line_vals.get('account_id'):
                                        account = self.env['account.account'].browse(line_vals['account_id'])
                                        if getattr(account, 'company_id', bill.company_id) == bill.company_id:
                                            minimal_line_vals['account_id'] = account.id
                                        else:
                                            # Find replacement or default
                                            default_account = _search_account_safe(
                                                self.env, [('internal_group', '=', 'expense')],
                                                company_id=bill.company_id.id, limit=1
                                            )
                                            if default_account:
                                                minimal_line_vals['account_id'] = default_account.id
                                    
                                    # Fix tax inconsistencies
                                    if line_vals.get('tax_ids'):
                                        # Only include taxes from same company
                                        tax_ids = line_vals['tax_ids'][0][2]
                                        valid_taxes = self.env['account.tax'].search([
                                            ('id', 'in', tax_ids), ('company_id', '=', bill.company_id.id)
                                        ])
                                        if valid_taxes:
                                            minimal_line_vals['tax_ids'] = [(6, 0, valid_taxes.ids)]
                                        
                                    # Create with minimal fields
                                    created_line = self.env['account.move.line'].with_company(bill.company_id.id).sudo().create(minimal_line_vals)
                                    successful_lines += 1
                                    _logger.info("✅ Created vendor bill line %s/%s with minimal fields", line_idx + 1, total_lines)
                                    
                                except Exception as fallback_error:
                                    _logger.error("❌ CRITICAL: Minimal fallback failed for line %s: %s", line_id, str(fallback_error))
                                    failed_lines += 1
                                    try:
                                        _log_failed_bill_migration(bill.name, f"Line {line_id} failed: {str(fallback_error)[:200]}")
                                    except:
                                        pass
                        
                        except Exception as line_process_error:
                            _logger.error("❌ CRITICAL: Unhandled error processing line %s: %s", line_id, str(line_process_error), exc_info=True)
                            failed_lines += 1

                    # Final status update after all lines migrated
                    try:
                        if failed_lines > 0:
                            status_msg = f'Migrated {successful_lines}/{total_lines} lines ({failed_lines} failed), finalizing...'
                            _logger.warning("⚠️ Line migration completed with failures: %s successful, %s failed out of %s total", 
                                          successful_lines, failed_lines, total_lines)
                        else:
                            status_msg = f'Migrated {successful_lines}/{total_lines} lines, finalizing...'
                            _logger.info("✅ All %s lines migrated successfully", total_lines)
                        
                        # Check if transaction is aborted before writing
                        try:
                            self.env.cr.execute("SELECT 1")
                        except Exception as check_error:
                            if 'current transaction is aborted' in str(check_error).lower():
                                _logger.warning("⚠️ Transaction aborted, rolling back before final status update...")
                                self.env.cr.rollback()
                        
                        self.write({
                            'status_message': status_msg,
                        })
                        self.env.cr.commit()
                    except Exception as final_error:
                        error_msg = str(final_error).lower()
                        if 'current transaction is aborted' in error_msg:
                            try:
                                self.env.cr.rollback()
                                _logger.warning("⚠️ Rolled back transaction, retrying final status update...")
                                # Retry after rollback
                                self.write({
                                    'status_message': status_msg,
                                })
                                self.env.cr.commit()
                            except:
                                pass  # Non-critical
                        else:
                            _logger.debug("Could not update final status: %s", str(final_error))
                except Exception as e:
                    error_msg = str(e)
                    _logger.error("❌ CRITICAL ERROR: Exception during line migration for bill %s: %s", 
                                self.uploaded_bill_number, error_msg, exc_info=True)
                    _logger.error("   This may have prevented lines from being created!")
                    
                    # CRITICAL: Rollback transaction if it's aborted
                    if 'current transaction is aborted' in error_msg.lower() or 'transaction' in error_msg.lower():
                        _logger.error("   Transaction aborted, rolling back...")
                        try:
                            self.env.cr.rollback()
                            _logger.info("   ✅ Transaction rolled back successfully")
                        except Exception as rollback_error:
                            _logger.error("   ❌ Failed to rollback: %s", str(rollback_error))
                    
                    # Re-raise to ensure we know about this critical error
                    raise
            
            self.env.cr.commit()
            
            # CRITICAL: Refresh bill to get latest lines and amounts after migration
            # Force a full refresh to ensure we see all created lines
            self.env.cr.commit()
            bill.invalidate_recordset(['invoice_line_ids', 'line_ids', 'amount_total', 'amount_untaxed', 'amount_tax', 'state'])
            # Reload bill to get fresh data
            bill = self.env['account.move'].browse(bill.id)
            
            # Recompute taxes and amounts to ensure VAT is calculated correctly
            try:
                # Trigger tax computation on all lines
                for line in bill.line_ids:
                    if line.tax_ids:
                        try:
                            # Force recomputation of tax-related fields
                            line._compute_tax_amount()
                            line._compute_price_subtotal()
                        except:
                            pass  # Some methods might not exist, continue
                
                # Try to recompute bill totals
                try:
                    if hasattr(bill, '_recompute_tax_lines'):
                        bill._recompute_tax_lines()
                    if hasattr(bill, '_recompute_dynamic_lines'):
                        bill._recompute_dynamic_lines()
                    if hasattr(bill, '_recompute_payment_terms_lines'):
                        bill._recompute_payment_terms_lines()
                except:
                    pass
                
                # Refresh after recomputation
                bill.invalidate_recordset(['line_ids', 'amount_total', 'amount_untaxed', 'amount_tax'])
                self.env.cr.commit()
            except Exception as recompute_error:
                _logger.warning("⚠️ Could not recompute taxes/amounts: %s", str(recompute_error))
            
            # Refresh bill to ensure we get accurate line counts
            bill.invalidate_recordset(['invoice_line_ids', 'line_ids'])
            # Reload bill to get fresh data
            bill = self.env['account.move'].browse(bill.id)
            
            # CRITICAL: Query database directly to verify lines exist (bypass ORM cache)
            # In Odoo 19, invoice lines are determined by display_type IS NULL and having product/account
            try:
                self.env.cr.execute("""
                    SELECT COUNT(*) 
                    FROM account_move_line 
                    WHERE move_id = %s
                    AND display_type IS NULL
                    AND (product_id IS NOT NULL OR account_id IS NOT NULL)
                """, (bill.id,))
                db_invoice_lines_count = self.env.cr.fetchone()[0] or 0
            except Exception as db_query_error:
                _logger.warning("⚠️ Could not query database for line count: %s, using ORM count instead", str(db_query_error))
                db_invoice_lines_count = 0  # Fallback to ORM count
            
            # Count invoice lines via ORM (not all line_ids, which includes tax lines, etc.)
            # CRITICAL: Check if transaction is aborted before ORM operations
            try:
                self.env.cr.execute("SELECT 1")
            except Exception as check_error:
                if 'current transaction is aborted' in str(check_error).lower():
                    _logger.warning("⚠️ Transaction aborted before counting lines, rolling back...")
                    try:
                        self.env.cr.rollback()
                        _logger.info("   ✅ Transaction rolled back successfully")
                        # Reload bill after rollback
                        bill.invalidate_recordset(['invoice_line_ids', 'line_ids'])
                        bill = self.env['account.move'].browse(bill.id)
                    except:
                        pass
            
            invoice_lines_count = len(bill.invoice_line_ids) if bill.invoice_line_ids else 0
            all_lines_count = len(bill.line_ids) if bill.line_ids else 0
            
            _logger.info("=" * 80)
            _logger.info("📊 BILL MIGRATION SUMMARY for %s:", bill.name)
            _logger.info("   Invoice Lines (ORM): %s", invoice_lines_count)
            _logger.info("   Invoice Lines (DB Query): %s", db_invoice_lines_count)
            _logger.info("   Total Lines (including tax): %s", all_lines_count)
            _logger.info("   Total Amount: %s", bill.amount_total)
            _logger.info("   Untaxed Amount: %s", bill.amount_untaxed)
            
            # CRITICAL: If lines don't match, log detailed information
            if db_invoice_lines_count == 0 and invoice_lines_count == 0:
                _logger.error("❌ CRITICAL: NO INVOICE LINES FOUND in database or ORM for bill %s!", bill.name)
                _logger.error("   This means lines were NOT created successfully!")
                
                # Check if any lines exist at all (including tax lines)
                self.env.cr.execute("""
                    SELECT COUNT(*), array_agg(id) 
                    FROM account_move_line 
                    WHERE move_id = %s
                """, (bill.id,))
                result = self.env.cr.fetchone()
                total_db_lines = result[0] or 0
                line_ids = result[1] or []
                _logger.error("   Total lines in DB (all types): %s (IDs: %s)", total_db_lines, line_ids)
                
                # Check for lines that might not appear as invoice lines (display_type set or missing product/account)
                try:
                    self.env.cr.execute("""
                        SELECT COUNT(*), array_agg(id) 
                        FROM account_move_line 
                        WHERE move_id = %s
                        AND (display_type IS NOT NULL OR (product_id IS NULL AND account_id IS NULL))
                    """, (bill.id,))
                    result = self.env.cr.fetchone()
                    excluded_lines = result[0] or 0 if result else 0
                    excluded_ids = result[1] or [] if result else []
                    if excluded_lines > 0:
                        _logger.warning("   Lines that may not appear as invoice lines: %s (IDs: %s) - check display_type, product_id, account_id", 
                                      excluded_lines, excluded_ids)
                    else:
                        excluded_lines = 0
                        excluded_ids = []
                except Exception as excluded_query_error:
                    _logger.warning("⚠️ Could not query excluded lines: %s", str(excluded_query_error))
                    excluded_lines = 0
                    excluded_ids = []
            elif db_invoice_lines_count != invoice_lines_count:
                _logger.warning("⚠️ Mismatch: DB has %s invoice lines but ORM shows %s", 
                              db_invoice_lines_count, invoice_lines_count)
            _logger.info("   Tax Amount: %s", bill.amount_tax)
            _logger.info("=" * 80)
            
            # Update total_items_odoo19 with actual migrated lines count (use DB count as source of truth)
            actual_migrated_lines = max(db_invoice_lines_count, invoice_lines_count)
            try:
                self.write({
                    'total_items_odoo19': actual_migrated_lines,
                })
                self.env.cr.commit()
                _logger.info("✅ Updated total_items_odoo19: %s", actual_migrated_lines)
            except Exception as update_error:
                _logger.warning("⚠️ Could not update total_items_odoo19: %s", str(update_error))
            
            # CRITICAL: Verify lines were actually created
            if invoice_lines_count == 0 and db_invoice_lines_count == 0:
                _logger.error("❌ CRITICAL ERROR: No invoice lines were created for bill %s!", bill.name)
                _logger.error("   Expected to create %s lines", total_lines if 'total_lines' in locals() else 'unknown')
                _logger.error("   Successful lines counter: %s", successful_lines if 'successful_lines' in locals() else 'unknown')
                _logger.error("   Failed lines counter: %s", failed_lines if 'failed_lines' in locals() else 'unknown')
                # Don't raise error - let it continue, but log it clearly
            
            # Log tax details for each line
            tax_lines_count = 0
            for line in bill.line_ids:
                if line.tax_ids:
                    tax_lines_count += 1
                    _logger.info("   Line '%s': Tax IDs: %s, Tax Names: %s, Price: %s, Subtotal: %s", 
                               line.name[:50] if line.name else 'N/A', 
                               line.tax_ids.ids, 
                               ', '.join(line.tax_ids.mapped('name')),
                               line.price_unit,
                               line.price_subtotal)
            
            if tax_lines_count == 0:
                _logger.warning("⚠️ No taxes found on any lines for bill %s", bill.name)
            
            # Post bill if it should be posted (from Odoo 14 state or Excel status)
            # ALWAYS post if Excel status says "Posted"
            if should_post:
                try:
                    # Refresh bill to get latest line counts
                    bill.invalidate_recordset(['invoice_line_ids', 'line_ids'])
                    # Reload bill to get fresh data
                    bill = self.env['account.move'].browse(bill.id)
                    
                    # Verify bill has invoice lines (required for posting)
                    invoice_lines = bill.invoice_line_ids
                    if not invoice_lines or len(invoice_lines) == 0:
                        _logger.error("❌ CRITICAL: Vendor bill %s has NO invoice lines after migration - cannot post!", bill.name)
                        _logger.error("   Bill will remain in draft state")
                        _logger.error("   Expected lines: %s", total_lines if 'total_lines' in locals() else 'unknown')
                        _logger.error("   Successful: %s, Failed: %s", 
                                    successful_lines if 'successful_lines' in locals() else 'unknown',
                                    failed_lines if 'failed_lines' in locals() else 'unknown')
                        should_post = False
                    else:
                        _logger.info("📝 Posting vendor bill %s (Excel status: %s, Odoo 14 state: %s)", 
                                   bill.name, self.excel_status or 'N/A', bill_data.get('state', 'N/A'))
                        _logger.info("   Bill has %s lines, total amount: %s", len(bill.line_ids), bill.amount_total)
                        
                        if bill.state != 'draft':
                            _logger.warning("⚠️ Vendor bill %s is not in draft state (%s), resetting to draft", bill.name, bill.state)
                            bill.button_draft()
                            self.env.cr.commit()
                        
                        bill.action_post()
                        self.env.cr.commit()
                        
                        # Refresh to get updated state and payment_state
                        bill.invalidate_recordset(['state', 'payment_state', 'amount_total', 'amount_untaxed', 'amount_tax'])
                        _logger.info("✅ Successfully posted vendor bill %s", bill.name)
                        _logger.info("   Final State: %s", bill.state)
                        _logger.info("   Payment State: %s", bill.payment_state)
                        _logger.info("   Total Amount: %s", bill.amount_total)
                        
                        # Verify payment_state is 'not_paid' (should be automatic, but log if not)
                        if bill.payment_state != 'not_paid':
                            _logger.warning("⚠️ Payment state for bill %s is %s (expected: not_paid)", bill.name, bill.payment_state)
                        
                        # Migrate payments linked to this bill from Odoo 14
                        try:
                            _logger.info("💳 Starting payment migration for bill %s", bill.name)
                            payments_odoo14 = self._fetch_payments_from_odoo14(client, bill_data['id'])
                            
                            if payments_odoo14:
                                _logger.info("📋 Found %s payment(s) to migrate for bill %s", len(payments_odoo14), bill.name)
                                created_payments = self._migrate_payments(client, bill, payments_odoo14)
                                _logger.info("✅ Successfully migrated %s payment(s) for bill %s", len(created_payments), bill.name)
                                
                                # Refresh bill to verify payment_state remains "not_paid" (payments not reconciled)
                                bill.invalidate_recordset(['payment_state', 'amount_residual'])
                                if bill.payment_state != 'not_paid':
                                    _logger.warning("⚠️ Payment state changed to %s (expected: not_paid) - payments were not reconciled", 
                                                  bill.payment_state)
                                else:
                                    _logger.info("   ✅ Payment State: %s (payments created but not reconciled)", bill.payment_state)
                                _logger.info("   Residual Amount: %s", bill.amount_residual)
                            else:
                                _logger.info("📋 No payments found for bill %s in Odoo 14", bill.name)
                        except Exception as payment_error:
                            _logger.warning("⚠️ Error migrating payments for bill %s: %s", bill.name, str(payment_error), exc_info=True)
                            # Don't fail the entire migration if payment migration fails
                except Exception as e:
                    _logger.warning("⚠️ Could not post vendor bill %s: %s", bill.name, str(e), exc_info=True)
                    should_post = False
            else:
                _logger.info("📋 Vendor bill %s will remain in draft state (Excel: %s, Odoo 14: %s)", 
                           bill.name, self.excel_status or 'N/A', bill_data.get('state', 'N/A'))
            
            # Update status to migrated with retry on serialization errors
            def _update_status_migrated():
                self.write({
                    'status': 'migrated',
                    'status_message': 'Successfully migrated',
                    'odoo19_bill_id': bill.id,
                    'odoo19_purchase_order_id': purchase_order.id if purchase_order else False,
                    'in_system_bill_number': bill.name,
                    'migration_date': fields.Datetime.now(),
                    'error_message': False,
                })
                self.env.cr.commit()
            
            try:
                _retry_on_serialization_error(_update_status_migrated)
            except Exception as e:
                _logger.error("Failed to update status to migrated after retries: %s", str(e))
                # Try one more time with fresh record
                try:
                    self.invalidate_recordset(['status'])
                    if self.status != 'migrated':
                        self.write({
                            'status': 'migrated',
                            'status_message': 'Successfully migrated',
                            'odoo19_bill_id': bill.id,
                            'odoo19_purchase_order_id': purchase_order.id if purchase_order else False,
                            'in_system_bill_number': bill.name,
                            'migration_date': fields.Datetime.now(),
                            'error_message': False,
                        })
                        self.env.cr.commit()
                except Exception as retry_error:
                    _logger.error("Failed to update status even after refresh: %s", str(retry_error))
                    raise
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'vendor.bill.migration.line',
                'view_mode': 'list,form',
                'target': 'current',
            }
                
        except UserError:
            raise
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error in action_migrate: %s", error_msg, exc_info=True)
            
            # Update status to error with retry on serialization errors
            def _update_status_error():
                self.write({
                    'status': 'error',
                    'status_message': 'Error: %s' % error_msg,
                    'error_message': error_msg,
                })
                self.env.cr.commit()
            
            try:
                _retry_on_serialization_error(_update_status_error)
            except Exception as update_error:
                _logger.error("Failed to update status to error after retries: %s", str(update_error))
                # Try one more time with fresh record
                try:
                    self.invalidate_recordset(['status'])
                    self.write({
                        'status': 'error',
                        'status_message': 'Error: %s' % error_msg,
                        'error_message': error_msg,
                    })
                    self.env.cr.commit()
                except Exception as retry_error:
                    _logger.error("Failed to update status to error even after refresh: %s", str(retry_error))
                    # Last resort: log to file
                    _log_failed_bill_migration(self.uploaded_bill_number, f"Migration failed and status update failed: {error_msg}")
            
            _log_failed_bill_migration(self.uploaded_bill_number, error_msg)
            raise UserError('Error migrating vendor bill: %s' % str(e))
    
    def _migrate_sequential(self, record_ids, current_index):
        """Sequential migration method using Queue Jobs"""
        if current_index >= len(record_ids):
            _logger.info("Sequential migration completed for all %s records", len(record_ids))
            return
        
        record_id = record_ids[current_index]
        record = self.env['vendor.bill.migration.line'].browse(record_id)
        
        if not record.exists():
            _logger.warning("Record %s does not exist, skipping", record_id)
            if current_index + 1 < len(record_ids):
                next_record = record.env['vendor.bill.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        bill_number = record.uploaded_bill_number
        _logger.info("🚀 Starting migration %s/%s: %s (record_id=%s)", current_index + 1, len(record_ids), bill_number, record_id)
        
        if record.status not in ('pending_migration', 'queued'):
            _logger.warning("Record %s is not in pending_migration or queued status (%s), skipping", bill_number, record.status)
            if current_index + 1 < len(record_ids):
                next_record = record.env['vendor.bill.migration.line'].browse(record_ids[current_index + 1])
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
                next_record = record.env['vendor.bill.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        record.write({
            'status': 'migrating',
            'status_message': 'Migration in progress...',
        })
        record.env.flush_all()
        _logger.info("📝 Status updated to 'migrating' for %s", bill_number)
        
        try:
            record.action_migrate()
            _logger.info("✅ Successfully migrated %s (%s/%s)", bill_number, current_index + 1, len(record_ids))
        except Exception as e:
            error_msg = str(e)
            _logger.error("❌ Error migrating vendor bill %s: %s", bill_number, error_msg, exc_info=True)
            
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
                next_record = fresh_env['vendor.bill.migration.line'].browse(next_record_id)
                
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

