# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
import uuid
from datetime import datetime

_logger = logging.getLogger(__name__)


def _log_failed_rfq_migration(rfq_number, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        # Get log directory (use module directory/logs)
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_rfq_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {rfq_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed RFQ migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed migrations log: %s", str(e))


def _check_queue_job_available(env):
    """Comprehensive check if queue_job is available and working"""
    # Check 1: Is module installed in database?
    try:
        module = env['ir.module.module'].search([
            ('name', '=', 'queue_job'),
            ('state', '=', 'installed')
        ], limit=1)
        if not module:
            return False, 'Module not installed in database'
    except Exception as e:
        return False, f'Error checking database: {str(e)}'
    
    # Check 2: Is module loaded in registry?
    try:
        if 'queue.job' not in env.registry:
            return False, 'Module not loaded in registry (restart needed)'
    except Exception as e:
        return False, f'Error checking registry: {str(e)}'
    
    # Check 3: Can we import the Job class?
    try:
        from odoo.addons.queue_job.job import Job
    except ImportError as e:
        return False, f'Cannot import Job class: {str(e)}'
    
    # Check 4: Is with_delay method available on models?
    try:
        test_model = env['res.users']
        if not hasattr(test_model, 'with_delay'):
            return False, 'with_delay method not available (restart needed)'
    except Exception as e:
        return False, f'Error checking with_delay: {str(e)}'
    
    return True, 'OK'


class RFQMigrationLine(models.Model):
    """Model to store uploaded RFQ numbers and track migration status"""
    _name = 'rfq.migration.line'
    _description = 'RFQ Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    uploaded_rfq_number = fields.Char(
        string='RFQ Number',
        required=True,
        index=True,
        help='RFQ number from Excel upload'
    )
    
    in_system_rfq_number = fields.Char(
        string='In-System RFQ Number',
        readonly=True,
        help='Actual RFQ number found in Odoo 14 or Odoo 19'
    )
    
    # Additional fields from Excel
    priority = fields.Char(
        string='Priority',
        help='Priority from Excel'
    )
    
    vendor = fields.Char(
        string='Vendor',
        help='Vendor name from Excel'
    )
    
    project = fields.Char(
        string='Project',
        help='Project name from Excel'
    )
    
    purchase_representative = fields.Char(
        string='Purchase Representative',
        help='Purchase Representative from Excel'
    )
    
    order_deadline = fields.Char(
        string='Order Deadline',
        help='Order Deadline from Excel'
    )
    
    excel_status = fields.Char(
        string='Status (Excel)',
        help='Status from Excel file'
    )
    
    company = fields.Char(
        string='Company/Branch',
        help='Company/Branch name from Excel'
    )
    
    created_on = fields.Char(
        string='Created On',
        help='Created On date from Excel'
    )
    
    effective_date = fields.Char(
        string='Effective Date',
        help='Effective Date from Excel'
    )
    
    receipt_date = fields.Char(
        string='Receipt Date',
        help='Receipt Date from Excel'
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
    
    odoo14_rfq_id = fields.Integer(
        string='Odoo 14 RFQ ID',
        readonly=True,
        help='ID of RFQ in Odoo 14 if found'
    )
    
    odoo19_rfq_id = fields.Many2one(
        'purchase.order',
        string='Odoo 19 RFQ',
        readonly=True,
        help='Migrated RFQ in Odoo 19'
    )
    
    migration_date = fields.Datetime(string='Migration Date', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    def check_status(self, rfq_number=None, config_id=None):
        """Check status of an RFQ number against Odoo 14 and Odoo 19"""
        self.ensure_one()
        if not rfq_number:
            rfq_number = self.uploaded_rfq_number
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
            existing_19 = self.env['purchase.order'].search([
                ('name', '=', rfq_number)
            ], limit=1)
            
            if existing_19:
                return {
                    'status': 'already_migrated',
                    'message': 'Already exists in Odoo 19',
                    'odoo19_id': existing_19.id,
                    'odoo19_name': existing_19.name
                }
            
            # Check in Odoo 14
            rfqs = client.search_read(
                'purchase.order',
                [('name', '=', rfq_number)],
                ['id', 'name'],
                limit=1
            )
            
            if rfqs:
                return {
                    'status': 'pending_migration',
                    'message': 'Found in Odoo 14, ready to migrate',
                    'odoo14_id': rfqs[0]['id'],
                    'odoo14_name': rfqs[0]['name']
                }
            else:
                return {
                    'status': 'not_found',
                    'message': 'Not found in Odoo 14'
                }
                
        except Exception as e:
            _logger.error("Error checking RFQ status: %s", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def action_check_status(self):
        """Button action to refresh status"""
        for record in self:
            result = record.check_status()
            record.write({
                'status': result.get('status', 'not_found'),
                'status_message': result.get('message', ''),
                'in_system_rfq_number': result.get('odoo14_name') or result.get('odoo19_name') or '',
                'odoo14_rfq_id': result.get('odoo14_id', 0),
                'odoo19_rfq_id': result.get('odoo19_id', False),
            })
    
    @api.model
    def action_open_upload_wizard(self):
        """Open the Excel upload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rfq.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': 'Upload Excel',
        }
    
    def action_trigger_queue_job_runner(self):
        """Manually trigger the queue job runner to process pending jobs immediately"""
        try:
            # Check if queue_job module is available
            if 'queue.job' not in self.env.registry:
                raise UserError(
                    'Queue Job module is not loaded.\n\n'
                    'Please:\n'
                    '1. Install "queue_job" module from Apps menu\n'
                    '2. Restart Odoo server'
                )
            
            # Count jobs by state
            pending_jobs = self.env['queue.job'].search_count([('state', '=', 'pending')])
            started_jobs = self.env['queue.job'].search_count([('state', '=', 'started')])
            
            # Check for RFQ migration-specific jobs
            migration_pending = self.env['queue.job'].search_count([
                ('state', '=', 'pending'),
                ('model_name', '=', 'rfq.migration.line'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            migration_started = self.env['queue.job'].search_count([
                ('state', '=', 'started'),
                ('model_name', '=', 'rfq.migration.line'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            
            _logger.info("📊 Queue status: %s pending (total), %s started (total), %s RFQ migration pending, %s RFQ migration started", 
                        pending_jobs, started_jobs, migration_pending, migration_started)
            
            # Check if queue_job_cron_jobrunner module is installed
            cron_jobrunner_module = self.env['ir.module.module'].search([
                ('name', '=', 'queue_job_cron_jobrunner'),
                ('state', '=', 'installed')
            ], limit=1)
            
            if not cron_jobrunner_module:
                raise UserError(
                    'Queue Job Cron Jobrunner module is not installed.\n\n'
                    'Please:\n'
                    '1. Go to Apps menu\n'
                    '2. Remove "Apps" filter (if any)\n'
                    '3. Search for "queue_job_cron_jobrunner"\n'
                    '4. Click "Install"\n'
                    '5. Restart Odoo server\n\n'
                    f'Currently {pending_jobs} job(s) are pending in the queue.'
                )
            
            # Try to trigger the cron job runner
            cron_job = self.env['ir.cron'].search([
                ('name', '=', 'Queue Job Runner'),
                ('model_id.model', '=', 'queue.job'),
            ], limit=1)
            
            if cron_job:
                try:
                    cron_job.method_direct_trigger()
                    _logger.info("✅ Triggered Queue Job Runner cron job")
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Queue Job Runner Triggered',
                            'message': f'Queue job runner has been triggered. Processing {pending_jobs} pending job(s)...',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                except Exception as e:
                    _logger.warning("Could not trigger cron job directly: %s", str(e))
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Queue Job Runner',
                            'message': f'Queue job runner will process jobs automatically. Currently {pending_jobs} pending job(s).',
                            'type': 'info',
                            'sticky': False,
                        }
                    }
            else:
                # Create cron job if it doesn't exist
                queue_job_model = self.env['ir.model'].search([('model', '=', 'queue.job')], limit=1)
                if queue_job_model:
                    queue_job_model_id = queue_job_model.id
                    self.env['ir.cron'].create({
                        'name': 'Queue Job Runner',
                        'model_id': queue_job_model_id,
                        'state': 'code',
                        'code': 'model._job_runner()',
                        'queue_job_runner': True,
                        'user_id': self.env.ref('base.user_root').id,
                        'interval_number': 1,
                        'interval_type': 'minutes',
                        'active': True,
                    })
                    _logger.info("✅ Created Queue Job Runner cron job")
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Queue Job Runner Created',
                            'message': f'Queue job runner cron job has been created. It will process {pending_jobs} pending job(s)...',
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    raise UserError('Could not find queue.job model')
                    
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error triggering queue job runner: %s", str(e), exc_info=True)
            raise UserError(f'Error triggering queue job runner: {str(e)}')
    
    def action_bulk_migrate(self):
        """Mark selected RFQs as 'queued' for sequential migration"""
        pending = self.filtered(lambda l: l.status == 'pending_migration')
        if not pending:
            raise UserError('No RFQs with "Pending Migration" status selected')
        
        # Comprehensive check if queue_job is available
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
        
        # Get IDs of pending records
        pending_ids = pending.ids
        
        if not pending_ids:
            raise UserError('No RFQs with "Pending Migration" status selected')
        
        # Mark all records as "queued" - user will start the migration process separately
        fresh_pending = self.env['rfq.migration.line'].browse(pending_ids)
        for record in fresh_pending:
            record.write({
                'status': 'queued',
                'status_message': 'Queued for migration - waiting to be processed',
                'error_message': False,
            })
        self.env.cr.commit()
        _logger.info("✅ Marked %s RFQs as 'queued' (ready for processing)", len(fresh_pending))
        
        # Return success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'RFQs Queued',
                'message': f'{len(pending_ids)} RFQs have been queued. Use "Process Queue Jobs Now" to start the migration process.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_start_queued_migration(self):
        """Start processing queued RFQs - enqueue the first job to start sequential migration"""
        queued = self.filtered(lambda l: l.status == 'queued')
        if not queued:
            raise UserError('No RFQs with "Queued" status selected')
        
        # Comprehensive check if queue_job is available
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
        
        # Get IDs of queued records
        queued_ids = queued.ids
        
        if not queued_ids:
            raise UserError('No RFQs with "Queued" status selected')
        
        # Start sequential migration by enqueueing the first job
        try:
            first_record = self.browse(queued_ids[0])
            if not first_record.exists():
                raise UserError(f'Record {queued_ids[0]} no longer exists')
            
            # Enqueue the first job - it will automatically process the rest sequentially
            job = first_record.with_delay()._migrate_sequential(queued_ids, 0)
            
            _logger.info("✅ Started sequential migration for %s queued RFQs (job UUID: %s)", 
                        len(queued_ids), getattr(job, 'uuid', 'N/A'))
            
            # Update status message
            queued.write({
                'status_message': 'Migration process started - job enqueued',
            })
            self.env.cr.commit()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Migration Started',
                    'message': f'Started processing {len(queued_ids)} queued RFQs. Migration will continue sequentially.',
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
        """Migrate this RFQ from Odoo 14 to Odoo 19"""
        self.ensure_one()
        
        if self.status not in ('pending_migration', 'queued'):
            raise UserError('Can only migrate RFQs with "Pending Migration" or "Queued" status')
        
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
            
            # Get initial RFQ data from Odoo 14
            safe_initial_fields = ['id', 'name']
            rfqs = client.search_read(
                'purchase.order',
                [('name', '=', self.uploaded_rfq_number)],
                safe_initial_fields,
                limit=1
            )
            
            if not rfqs:
                self.write({
                    'status': 'not_found',
                    'status_message': 'RFQ not found in Odoo 14',
                })
                return
            
            rfq_data = rfqs[0]
            
            # Check if RFQ already exists in Odoo 19 BEFORE migrating
            existing_rfq = self.env['purchase.order'].search([
                ('name', '=', self.uploaded_rfq_number)
            ], limit=1)
            
            if existing_rfq:
                _logger.info("RFQ %s already exists in Odoo 19 (ID: %s), marking as migrated", 
                           self.uploaded_rfq_number, existing_rfq.id)
                self.write({
                    'status': 'migrated',
                    'status_message': 'Already migrated (existed in system)',
                    'odoo19_rfq_id': existing_rfq.id,
                    'in_system_rfq_number': existing_rfq.name,
                    'migration_date': fields.Datetime.now(),
                    'error_message': False,
                })
                self.env.cr.commit()
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'rfq.migration.line',
                    'view_mode': 'list,form',
                    'target': 'current',
                }
            
            # Update status to migrating
            self.write({
                'status': 'migrating',
                'status_message': 'Migration in progress...',
            })
            self.env.cr.commit()
            
            # Get fields to fetch - include custom fields from eq_fc_purchase_custom
            excluded_fields = [
                'display_name', 'name_get', 'name_search',
            ]
            
            # Standard purchase.order fields
            base_fields_to_fetch = [
                'id', 'name', 'partner_id', 'date_order', 'date_planned', 'date_approve',
                'state', 'currency_id', 'picking_type_id', 'company_id', 'user_id',
                'order_line', 'invoice_ids', 'picking_ids', 'notes', 'note', 'origin',
                'create_date', 'write_date', 'write_uid', 'create_uid',
                # Standard Odoo fields
                'incoterm_id', 'payment_term_id', 'fiscal_position_id',
                # Custom fields from metro_erp (Odoo 14) / eq_fc_purchase_custom (Odoo 19)
                'attention', 'delivery_address', 'attention_mobile_number', 'is_with_stamp',
                'is_wo_header', 'is_lumpsum', 'attention_note', 'ask_confirmation',
                'receipt_date', 'deliver_to', 'verified_by', 'approved_by',
                'project_code', 'project', 'order_contact', 'contact_no',
                'supplier_quote_ref', 'internal_notes', 'sale_order_reference',
                # Fields from metro_erp module (UH Metro ERP) - Additional fields
                'revision_id', 'is_account_approval', 'is_approval', 'approval_id',
                # Fields from Odoo 14 modules (odx_purchase_customisation, odx_purchase_generation)
                'project_id', 'branch_id', 'is_synced', 'is_manually_sync', 'is_from_project',
                # Fields from project_sale module
                'projects_line', 'delivery_line', 'delivery_partner_id',
                # Fields from tis_sales_purchase_global_discount module
                'discount_type', 'discount_rate', 'discount_narration', 'retention_rate',
                'amount_discount', 'is_tax_after_discount',
            ]

            # Remove fields that do not exist on the Odoo 14 instance (prevents Invalid field errors)
            fields_to_fetch = list(base_fields_to_fetch)
            try:
                po_fields = client.fields_get('purchase.order')
                fields_to_fetch = [f for f in fields_to_fetch if f in po_fields]
            except Exception as e:
                _logger.warning("Could not fetch purchase.order fields_get: %s", str(e))
            
            # Try to get all fields dynamically
            try:
                all_fields = client.fields_get('purchase.order')
                if all_fields:
                    dynamic_fields = []
                    for f, field_info in all_fields.items():
                        if f in excluded_fields or f in fields_to_fetch:
                            continue
                        field_type = field_info.get('type', '')
                        field_store = field_info.get('store', True)
                        if not field_store:
                            continue
                        if field_type in ('one2many', 'many2many') and f not in ('order_line',):
                            continue
                        if field_type in ('char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime', 'many2one', 'selection'):
                            dynamic_fields.append(f)
                    fields_to_fetch = list(set(fields_to_fetch + dynamic_fields))
            except Exception as e:
                _logger.warning("Could not get all fields: %s", str(e))
            
            minimal_safe_fields = [
                'id', 'name', 'partner_id', 'date_order', 'date_planned', 'state',
                'currency_id', 'company_id', 'order_line', 'create_date', 'write_date'
            ]
            
            try:
                full_rfq = client.search_read(
                    'purchase.order',
                    [('id', '=', rfq_data['id'])],
                    fields_to_fetch,
                    limit=1
                )
            except Exception as e:
                _logger.warning("Error fetching RFQ with expanded fields: %s. Using minimal safe fields.", str(e))
                full_rfq = client.search_read(
                    'purchase.order',
                    [('id', '=', rfq_data['id'])],
                    minimal_safe_fields,
                    limit=1
                )
            
            if not full_rfq:
                raise UserError('Could not fetch full RFQ data')
            
            rfq_data = full_rfq[0]
            
            # Try to read computed fields directly if they weren't fetched
            # Some fields like sale_order_reference might be computed but not stored
            computed_fields_to_try = ['sale_order_reference']
            for field_name in computed_fields_to_try:
                if field_name not in rfq_data or not rfq_data.get(field_name):
                    try:
                        direct_read = client.read('purchase.order', [rfq_data['id']], [field_name])
                        if direct_read and direct_read[0].get(field_name):
                            rfq_data[field_name] = direct_read[0][field_name]
                            _logger.debug("Fetched computed field %s via direct read: %s", field_name, rfq_data[field_name])
                    except Exception as e:
                        _logger.debug("Could not read computed field %s: %s", field_name, str(e))
            
            # Log what fields were actually fetched (for debugging)
            _logger.info("📋 Fetched RFQ data for %s. Available fields: %s", 
                        self.uploaded_rfq_number, list(rfq_data.keys()))
            
            # Log custom field values that were fetched
            custom_fields_to_log = [
                'attention', 'delivery_address', 'attention_mobile_number', 'is_with_stamp',
                'is_wo_header', 'is_lumpsum', 'project_code', 'project_id', 'project', 'order_contact',
                'contact_no', 'supplier_quote_ref', 'internal_notes', 'sale_order_reference',
                'verified_by', 'approved_by', 'receipt_date', 'deliver_to', 'user_id',
                'incoterm_id', 'payment_term_id', 'fiscal_position_id'
            ]
            for field in custom_fields_to_log:
                if field in rfq_data:
                    value = rfq_data.get(field)
                    if value:
                        _logger.info("  📌 %s = %s", field, value)
            
            # Use wizard helper to prepare RFQ values
            wizard = self.env['odoo14.customer.migration.wizard'].create({
                'config_id': self.config_id.id if self.config_id else False,
            })
            rfq_vals = wizard._prepare_rfq_vals(rfq_data, client)
            
            # Create RFQ in Odoo 19
            rfq = self.env['purchase.order'].create(rfq_vals)
            
            # Preserve original creation date and user info
            src_create_date = rfq_data.get('create_date')
            src_write_date = rfq_data.get('write_date')
            src_create_uid = rfq_data.get('create_uid')
            src_write_uid = rfq_data.get('write_uid')
            
            if src_create_date or src_write_date or src_create_uid or src_write_uid:
                try:
                    # Get user IDs
                    create_uid_val = None
                    write_uid_val = None
                    
                    if src_create_uid:
                        create_uid_id = src_create_uid[0] if isinstance(src_create_uid, list) else src_create_uid
                        if create_uid_id:
                            # Try to find user in Odoo 19 by Odoo 14 user ID or name
                            create_user = self.env['res.users'].browse(create_uid_id)
                            if not create_user.exists():
                                # Try to get user info from Odoo 14 and find by login/name
                                try:
                                    user_data = client.search_read(
                                        'res.users',
                                        [('id', '=', create_uid_id)],
                                        ['login', 'name', 'email'],
                                        limit=1
                                    )
                                    if user_data:
                                        user_info = user_data[0]
                                        # Search for user in Odoo 19
                                        create_user = self.env['res.users'].search([
                                            ('login', '=', user_info.get('login'))
                                        ], limit=1)
                                        if not create_user:
                                            create_user = self.env['res.users'].search([
                                                ('name', '=', user_info.get('name'))
                                            ], limit=1)
                                except Exception:
                                    pass
                            if create_user.exists():
                                create_uid_val = create_user.id
                    
                    if src_write_uid:
                        write_uid_id = src_write_uid[0] if isinstance(src_write_uid, list) else src_write_uid
                        if write_uid_id:
                            write_user = self.env['res.users'].browse(write_uid_id)
                            if not write_user.exists():
                                try:
                                    user_data = client.search_read(
                                        'res.users',
                                        [('id', '=', write_uid_id)],
                                        ['login', 'name', 'email'],
                                        limit=1
                                    )
                                    if user_data:
                                        user_info = user_data[0]
                                        write_user = self.env['res.users'].search([
                                            ('login', '=', user_info.get('login'))
                                        ], limit=1)
                                        if not write_user:
                                            write_user = self.env['res.users'].search([
                                                ('name', '=', user_info.get('name'))
                                            ], limit=1)
                                except Exception:
                                    pass
                            if write_user.exists():
                                write_uid_val = write_user.id
                    
                    # Update with original dates and users
                    update_fields = []
                    update_values = []
                    
                    if src_create_date:
                        update_fields.append("create_date = %s")
                        update_values.append(src_create_date)
                    
                    if src_write_date:
                        update_fields.append("write_date = %s")
                        update_values.append(src_write_date)
                    
                    if create_uid_val:
                        update_fields.append("create_uid = %s")
                        update_values.append(create_uid_val)
                    
                    if write_uid_val:
                        update_fields.append("write_uid = %s")
                        update_values.append(write_uid_val)
                    
                    if update_fields:
                        update_values.append(rfq.id)
                        self.env.cr.execute(
                            f"""
                            UPDATE purchase_order
                               SET {', '.join(update_fields)}
                             WHERE id = %s
                            """,
                            tuple(update_values),
                        )
                        _logger.info("✅ Preserved original dates and users for RFQ %s", rfq.name)
                except Exception as e:
                    _logger.warning("Could not set original create_date/write_date/users: %s", str(e))
            
            # Migrate purchase order lines - CRITICAL: Must migrate all products
            order_line_ids = rfq_data.get('order_line', [])
            _logger.info("=" * 80)
            _logger.info("🔍 PRODUCT LINE MIGRATION DEBUG for RFQ %s", self.uploaded_rfq_number)
            _logger.info("=" * 80)
            _logger.info("📋 Raw order_line from Odoo 14: %s", order_line_ids)
            _logger.info("📋 Type of order_line: %s", type(order_line_ids))
            _logger.info("📋 Length of order_line: %s", len(order_line_ids) if order_line_ids else 0)
            
            # If order_line is empty, try to fetch it directly
            if not order_line_ids:
                _logger.warning("⚠️ order_line is empty! Trying to fetch directly from Odoo 14...")
                try:
                    direct_rfq = client.read('purchase.order', [rfq_data['id']], ['order_line'])
                    if direct_rfq and direct_rfq[0].get('order_line'):
                        order_line_ids = direct_rfq[0]['order_line']
                        _logger.info("✅ Fetched order_line directly: %s", order_line_ids)
                except Exception as e:
                    _logger.error("❌ Could not fetch order_line directly: %s", str(e))
            
            if order_line_ids:
                # Extract IDs from order_line (could be list of IDs or list of tuples)
                line_ids = []
                for item in order_line_ids:
                    if isinstance(item, (list, tuple)) and len(item) > 0:
                        line_ids.append(item[0])  # Get ID from tuple
                    elif isinstance(item, int):
                        line_ids.append(item)  # Direct ID
                
                _logger.info("📦 Extracted %s line IDs from order_line for RFQ %s: %s", 
                            len(line_ids), self.uploaded_rfq_number, line_ids)
                
                if line_ids:
                    _logger.info("  ✅ Found %s line IDs to migrate: %s", len(line_ids), line_ids[:10])  # Show first 10
                    lines_created = 0
                    lines_failed = 0
                    try:
                        for idx, line_id in enumerate(line_ids, 1):
                            try:
                                _logger.info("  " + "="*70)
                                _logger.info("  🔄 Processing line %s/%s: Line ID %s", idx, len(line_ids), line_id)
                                _logger.info("  " + "="*70)
                                _logger.info("  🔄 Fetching purchase order line %s (%s/%s) from Odoo 14...", 
                                           line_id, idx, len(line_ids))
                                # Build safe field list for purchase.order.line based on fields_get
                                # Include all standard and custom fields that might exist
                                # CRITICAL: Ensure we fetch Product, Description (name), Qty, Unit Price, Taxes, Received Qty, Billed Qty
                                pol_fields = ['product_id', 'name', 'description', 'product_qty', 'product_uom', 'product_uom_id', 'price_unit',
                                              'qty_received', 'qty_invoiced',  # Received and Billed quantities
                                              'discount', 'taxes_id', 'tax_ids',  # Try both tax field names from Odoo 14
                                              'date_planned', 'sequence',
                                              'brand_id', 'project_id', 'customer_id', 'project_orderline_id', 'branch_id',
                                              'product_brand_id', 'brand_variant_id', 'expected_arrival', 'arrival_date',
                                              'analytic_distribution', 'account_analytic_id']
                                try:
                                    pol_fields_info = client.fields_get('purchase.order.line')
                                    pol_fields = [f for f in pol_fields if f in pol_fields_info]
                                except Exception as e:
                                    _logger.warning("Could not fetch purchase.order.line fields_get: %s", str(e))

                                line_data = client.search_read(
                                    'purchase.order.line',
                                    [('id', '=', line_id)],
                                    pol_fields,
                                    limit=1
                                )
                                if line_data:
                                    line_info = line_data[0]
                                    _logger.info("  📋 Line data fetched from Odoo 14:")
                                    _logger.info("     - product_id: %s", line_info.get('product_id'))
                                    _logger.info("     - name/description: %s", line_info.get('name', '')[:100] or line_info.get('description', '')[:100] or 'None')
                                    _logger.info("     - product_qty: %s", line_info.get('product_qty'))
                                    _logger.info("     - qty_received: %s", line_info.get('qty_received', 'Not found'))
                                    _logger.info("     - qty_invoiced: %s", line_info.get('qty_invoiced', 'Not found'))
                                    _logger.info("     - price_unit: %s", line_info.get('price_unit'))
                                    _logger.info("     - taxes_id/tax_ids: %s / %s", line_info.get('taxes_id'), line_info.get('tax_ids'))
                                    _logger.info("     - product_uom/product_uom_id: %s / %s", line_info.get('product_uom'), line_info.get('product_uom_id'))
                                    try:
                                        _logger.info("  🔄 Starting line creation process...")
                                        # Create line directly (like estimation migration does)
                                        # Get product
                                        product = False
                                        _logger.info("  🔍 Step 1: Looking for product...")
                                        if line_info.get('product_id'):
                                            product_id = line_info['product_id']
                                            product_id_val = product_id[0] if isinstance(product_id, (list, tuple)) else product_id
                                            if product_id_val:
                                                # First try to find by ID
                                                product = self.env['product.product'].browse(product_id_val)
                                                if not product.exists():
                                                    # Try to get from Odoo 14 and find by default_code or name
                                                    try:
                                                        product_data = client.search_read(
                                                            'product.product',
                                                            [('id', '=', product_id_val)],
                                                            ['name', 'default_code', 'barcode', 'list_price', 'type'],
                                                            limit=1
                                                        )
                                                        if product_data:
                                                            prod_data = product_data[0]
                                                            # Try to find by default_code first
                                                            if prod_data.get('default_code'):
                                                                product = self.env['product.product'].search([
                                                                    ('default_code', '=', prod_data['default_code'])
                                                                ], limit=1)
                                                            
                                                            # If still not found, try by barcode
                                                            if not product and prod_data.get('barcode'):
                                                                product = self.env['product.product'].search([
                                                                    ('barcode', '=', prod_data['barcode'])
                                                                ], limit=1)
                                                            
                                                            # If still not found, create it
                                                            if not product:
                                                                product_name = prod_data.get('name', 'Product')
                                                                product_type = prod_data.get('type', 'consu')
                                                                
                                                                # Validate product type
                                                                try:
                                                                    product_template_model = self.env['product.template']
                                                                    type_field = product_template_model._fields.get('type')
                                                                    if type_field and hasattr(type_field, 'selection'):
                                                                        valid_types = [v[0] for v in type_field.selection]
                                                                        if product_type not in valid_types:
                                                                            product_type = valid_types[0] if valid_types else 'consu'
                                                                except Exception:
                                                                    if product_type not in ('consu', 'service', 'product'):
                                                                        product_type = 'consu'
                                                                
                                                                # Create product template first
                                                                template_vals = {
                                                                    'name': product_name,
                                                                    'default_code': prod_data.get('default_code', ''),
                                                                    'list_price': prod_data.get('list_price', 0.0),
                                                                    'type': product_type,
                                                                    'purchase_ok': True,
                                                                }
                                                                product_template = self.env['product.template'].create(template_vals)
                                                                product = product_template.product_variant_id
                                                                
                                                                # Set barcode on product variant
                                                                if prod_data.get('barcode'):
                                                                    try:
                                                                        product.barcode = prod_data['barcode']
                                                                    except Exception:
                                                                        pass
                                                                
                                                                _logger.info("  ✅ Created product %s (ID: %s) for RFQ line", product.name, product.id)
                                                    except Exception as e:
                                                        _logger.error("  ❌ ERROR: Could not get/create product %s: %s", product_id_val, str(e), exc_info=True)
                                        
                                        if product:
                                            _logger.info("  ✅ Step 1 Complete: Product found/created - %s (ID: %s)", product.name, product.id)
                                        else:
                                            _logger.warning("  ⚠️ Step 1 Warning: No product found, will create fallback")
                                        
                                        # Get UoM
                                        _logger.info("  🔍 Step 2: Getting UoM...")
                                        uom = False
                                        if line_info.get('product_uom_id'):
                                            uom_id = line_info['product_uom_id']
                                            uom_id_val = uom_id[0] if isinstance(uom_id, (list, tuple)) else uom_id
                                            if uom_id_val:
                                                uom = self.env['uom.uom'].browse(uom_id_val)
                                                if not uom.exists():
                                                    uom = False
                                        if not uom and line_info.get('product_uom'):
                                            uom_id = line_info['product_uom']
                                            uom_id_val = uom_id[0] if isinstance(uom_id, (list, tuple)) else uom_id
                                            if uom_id_val:
                                                uom = self.env['uom.uom'].browse(uom_id_val)
                                                if not uom.exists():
                                                    # Try to get UoM from Odoo 14 and create it in Odoo 19
                                                    try:
                                                        uom_data = client.search_read(
                                                            'uom.uom',
                                                            [('id', '=', uom_id_val)],
                                                            ['name', 'category_id', 'factor', 'uom_type', 'rounding'],
                                                            limit=1
                                                        )
                                                        if uom_data:
                                                            uom_info = uom_data[0]
                                                            uom_name = uom_info.get('name', 'Unit')
                                                            # Check if UoM already exists by name
                                                            uom = self.env['uom.uom'].search([('name', '=', uom_name)], limit=1)
                                                            if not uom:
                                                                # Create UoM category if needed
                                                                category_id = uom_info.get('category_id')
                                                                category_id_val = category_id[0] if isinstance(category_id, (list, tuple)) else category_id
                                                                if category_id_val:
                                                                    category = self.env['uom.category'].browse(category_id_val)
                                                                    if not category.exists():
                                                                        # Get category from Odoo 14
                                                                        try:
                                                                            cat_data = client.search_read(
                                                                                'uom.category',
                                                                                [('id', '=', category_id_val)],
                                                                                ['name'],
                                                                                limit=1
                                                                            )
                                                                            if cat_data:
                                                                                cat_name = cat_data[0].get('name', 'Unit')
                                                                                category = self.env['uom.category'].search([('name', '=', cat_name)], limit=1)
                                                                                if not category:
                                                                                    category = self.env['uom.category'].create({'name': cat_name})
                                                                        except Exception:
                                                                            category = self.env['uom.category'].search([], limit=1)
                                                                    if category:
                                                                        uom_vals = {
                                                                            'name': uom_name,
                                                                            'category_id': category.id,
                                                                            'factor': uom_info.get('factor', 1.0),
                                                                            'uom_type': uom_info.get('uom_type', 'reference'),
                                                                            'rounding': uom_info.get('rounding', 0.01),
                                                                        }
                                                                        uom = self.env['uom.uom'].create(uom_vals)
                                                                        _logger.info("  ✅ Created UoM: %s (ID: %s)", uom.name, uom.id)
                                                                    else:
                                                                        _logger.warning("  ⚠️ Could not create UoM category, will use fallback")
                                                                else:
                                                                    _logger.warning("  ⚠️ No category ID found for UoM, will use fallback")
                                                    except Exception as uom_error:
                                                        _logger.warning("  ⚠️ Could not fetch/create UoM from Odoo 14: %s", str(uom_error))
                                                        uom = False
                                        
                                        if not uom:
                                            if product and hasattr(product, 'uom_id') and product.uom_id:
                                                uom = product.uom_id
                                                _logger.info("  ✅ Using product's default UoM: %s", uom.name)
                                            else:
                                                uom = self.env['uom.uom'].search([('name', '=', 'Units')], limit=1)
                                                if not uom:
                                                    uom = self.env['uom.uom'].search([('name', '=', 'Unit(s)')], limit=1)
                                                if not uom:
                                                    uom = self.env['uom.uom'].search([], limit=1)
                                                if uom:
                                                    _logger.info("  ✅ Using default UoM: %s", uom.name)
                                        
                                        _logger.info("  ✅ Step 2 Complete: UoM = %s (ID: %s)", uom.name if uom else 'None', uom.id if uom else 'N/A')
                                        
                                        # Prepare line values - CRITICAL: Ensure all required fields are set
                                        _logger.info("  🔍 Step 3: Preparing line values...")
                                        # Product, Description (name), Qty, Unit Price, Taxes, Amount (computed)
                                        line_description = line_info.get('name', '') or line_info.get('description', '') or ''
                                        if not line_description and product:
                                            line_description = product.name
                                        if not line_description:
                                            line_description = 'Line Item'
                                        
                                        # CRITICAL: product_uom_id is REQUIRED in Odoo 19 - must have a value
                                        if not uom:
                                            _logger.error("  ❌ CRITICAL: No UoM found! Cannot create line without UoM.")
                                            # Try one more time to get a UoM
                                            uom = self.env['uom.uom'].search([('name', '=', 'Unit(s)')], limit=1)
                                            if not uom:
                                                uom = self.env['uom.uom'].search([('name', '=', 'Units')], limit=1)
                                            if not uom:
                                                uom = self.env['uom.uom'].search([], limit=1)
                                            if uom:
                                                _logger.info("  ✅ Found fallback UoM: %s", uom.name)
                                            else:
                                                raise ValueError("Cannot create purchase order line: No UoM available in system!")
                                        
                                        # Product is required - ensure it's set before creating line_vals
                                        if not product:
                                            # Create fallback service product
                                            try:
                                                fallback_name = line_info.get('name', 'Line Item') or 'Line Item'
                                                fallback_code = f"MIGRATED_{uuid.uuid4().hex[:8]}"
                                                fallback_template = self.env['product.template'].create({
                                                    'name': fallback_name[:200],
                                                    'default_code': fallback_code,
                                                    'type': 'service',
                                                    'purchase_ok': True,
                                                    'sale_ok': False,
                                                })
                                                product = fallback_template.product_variant_id
                                                _logger.info("  ✅ Created fallback service product: %s (ID: %s)", product.name, product.id)
                                            except Exception as fallback_error:
                                                _logger.error("  ❌ Failed to create fallback product: %s", str(fallback_error))
                                                raise ValueError(f"Cannot create line without product: {fallback_error}")
                                        
                                        # Now create line_vals with all required fields
                                        line_vals = {
                                            'order_id': rfq.id,
                                            'product_id': product.id,  # Product (required - now guaranteed to exist)
                                            'name': line_description,  # Description field (required)
                                            'product_qty': float(line_info.get('product_qty', 0.0)) or 1.0,  # Qty (required)
                                            'product_uom_id': uom.id,  # UoM (REQUIRED - must have value)
                                            'price_unit': float(line_info.get('price_unit', 0.0)),  # Unit Price (required)
                                            'date_planned': line_info.get('date_planned') or rfq.date_planned or rfq.date_order,
                                        }
                                        
                                        # Map received quantity and billed quantity
                                        if line_info.get('qty_received') is not None:
                                            qty_received = float(line_info.get('qty_received', 0.0))
                                            line_vals['qty_received'] = qty_received
                                            _logger.info("  📦 Received Quantity: %s", qty_received)
                                        
                                        if line_info.get('qty_invoiced') is not None:
                                            qty_invoiced = float(line_info.get('qty_invoiced', 0.0))
                                            line_vals['qty_invoiced'] = qty_invoiced
                                            _logger.info("  💰 Billed Quantity: %s", qty_invoiced)
                                        
                                        _logger.info("  📝 Step 3 Complete: Line values prepared:")
                                        _logger.info("     - Product: %s (ID: %s)", product.name, product.id)
                                        _logger.info("     - Description: %s", line_description[:50])
                                        _logger.info("     - Quantity: %s", line_vals['product_qty'])
                                        _logger.info("     - Received Quantity: %s", line_vals.get('qty_received', 0.0))
                                        _logger.info("     - Billed Quantity: %s", line_vals.get('qty_invoiced', 0.0))
                                        _logger.info("     - Unit Price: %s", line_vals['price_unit'])
                                        _logger.info("     - UoM: %s (ID: %s)", uom.name, uom.id)
                                        
                                        # Map taxes - CRITICAL: Taxes field
                                        # In Odoo 19, purchase.order.line uses 'tax_ids' (not 'taxes_id')
                                        purchase_order_line_fields = self.env['purchase.order.line']._fields
                                        tax_field_name = None
                                        
                                        # Check which tax field exists in Odoo 19
                                        if 'tax_ids' in purchase_order_line_fields:
                                            tax_field_name = 'tax_ids'
                                        elif 'taxes_id' in purchase_order_line_fields:
                                            tax_field_name = 'taxes_id'
                                        
                                        if tax_field_name:
                                            # Get tax data from Odoo 14 (could be 'taxes_id' or 'tax_ids')
                                            tax_data = line_info.get('taxes_id') or line_info.get('tax_ids')
                                            
                                            if tax_data:
                                                valid_tax_ids = []
                                                # Handle both list of IDs and list of tuples
                                                if isinstance(tax_data, (list, tuple)):
                                                    for tax_item in tax_data:
                                                        tax_id_val = tax_item[0] if isinstance(tax_item, (list, tuple)) else tax_item
                                                        if tax_id_val:
                                                            tax = self.env['account.tax'].browse(tax_id_val)
                                                            if tax.exists():
                                                                valid_tax_ids.append(tax.id)
                                                
                                                if valid_tax_ids:
                                                    line_vals[tax_field_name] = [(6, 0, valid_tax_ids)]
                                                    _logger.info("  ✅ Mapped %s taxes to line using field '%s'", len(valid_tax_ids), tax_field_name)
                                                else:
                                                    _logger.warning("  ⚠️ No valid taxes found after mapping")
                                            else:
                                                _logger.info("  ℹ️ No taxes found in line data from Odoo 14")
                                        else:
                                            _logger.warning("  ⚠️ No tax field found on purchase.order.line model")
                                        
                                        # Map custom fields (purchase_order_line_fields already defined above for taxes)
                                        
                                        if 'brand_id' in purchase_order_line_fields and line_info.get('brand_id'):
                                            brand_id = line_info.get('brand_id')
                                            brand_id_val = brand_id[0] if isinstance(brand_id, (list, tuple)) else brand_id
                                            if brand_id_val:
                                                brand = self.env['product.brand'].browse(brand_id_val)
                                                if brand.exists():
                                                    line_vals['brand_id'] = brand.id
                                        
                                        if 'project_id' in purchase_order_line_fields and line_info.get('project_id'):
                                            project_id = line_info.get('project_id')
                                            project_id_val = project_id[0] if isinstance(project_id, (list, tuple)) else project_id
                                            if project_id_val:
                                                project = self.env['project.project'].browse(project_id_val)
                                                if project.exists():
                                                    line_vals['project_id'] = project.id
                                        
                                        if 'customer_id' in purchase_order_line_fields and line_info.get('customer_id'):
                                            customer_id = line_info.get('customer_id')
                                            customer_id_val = customer_id[0] if isinstance(customer_id, (list, tuple)) else customer_id
                                            if customer_id_val:
                                                customer = self.env['res.partner'].browse(customer_id_val)
                                                if customer.exists():
                                                    line_vals['customer_id'] = customer.id
                                        
                                        if line_info.get('sequence'):
                                            line_vals['sequence'] = line_info.get('sequence')
                                        
                                        # Map discount if available
                                        if line_info.get('discount'):
                                            line_vals['discount'] = line_info.get('discount')
                                        
                                        # Ensure date_planned is set (Expected Arrival)
                                        if not line_vals.get('date_planned'):
                                            from datetime import datetime
                                            line_vals['date_planned'] = rfq.date_planned or rfq.date_order or datetime.now()
                                        
                                        # Map analytic account if available
                                        if 'analytic_distribution' in purchase_order_line_fields and line_info.get('analytic_distribution'):
                                            line_vals['analytic_distribution'] = line_info.get('analytic_distribution')
                                        elif 'account_analytic_id' in purchase_order_line_fields and line_info.get('account_analytic_id'):
                                            account_analytic_id = line_info.get('account_analytic_id')
                                            account_analytic_id_val = account_analytic_id[0] if isinstance(account_analytic_id, (list, tuple)) else account_analytic_id
                                            if account_analytic_id_val:
                                                analytic_account = self.env['account.analytic.account'].browse(account_analytic_id_val)
                                                if analytic_account.exists():
                                                    line_vals['account_analytic_id'] = analytic_account.id
                                        
                                        # Map brand_variant_id if field exists (Brand Variant column)
                                        if 'brand_variant_id' in purchase_order_line_fields and line_info.get('brand_variant_id'):
                                            brand_variant_id = line_info.get('brand_variant_id')
                                            brand_variant_id_val = brand_variant_id[0] if isinstance(brand_variant_id, (list, tuple)) else brand_variant_id
                                            if brand_variant_id_val:
                                                brand_variant = self.env['product.brand.variant'].browse(brand_variant_id_val)
                                                if brand_variant.exists():
                                                    line_vals['brand_variant_id'] = brand_variant.id
                                        
                                        # Create the line directly (like estimation migration)
                                        # Log line values before creation for debugging
                                        # Get tax field name for logging
                                        tax_field_log = line_vals.get('tax_ids') or line_vals.get('taxes_id') or 'None'
                                        _logger.info("  🔧 Creating line with values: order_id=%s, product_id=%s, name=%s, qty=%s, price=%s, taxes=%s", 
                                                   line_vals.get('order_id'),
                                                   line_vals.get('product_id'),
                                                   line_vals.get('name', '')[:50],
                                                   line_vals.get('product_qty'),
                                                   line_vals.get('price_unit'),
                                                   tax_field_log)
                                        
                                        rfq_line = self.env['purchase.order.line'].create(line_vals)
                                        
                                        # Verify all fields were set correctly
                                        _logger.info("  ✅ Created RFQ line ID %s:", rfq_line.id)
                                        _logger.info("     - Product: %s (ID: %s)", 
                                                   rfq_line.product_id.name if rfq_line.product_id else 'No product',
                                                   rfq_line.product_id.id if rfq_line.product_id else 'N/A')
                                        _logger.info("     - Description: %s", rfq_line.name[:100] if rfq_line.name else 'No description')
                                        _logger.info("     - Quantity: %s %s", rfq_line.product_qty, rfq_line.product_uom_id.name if rfq_line.product_uom_id else '')
                                        _logger.info("     - Received Quantity: %s", getattr(rfq_line, 'qty_received', 0.0))
                                        _logger.info("     - Billed Quantity: %s", getattr(rfq_line, 'qty_invoiced', 0.0))
                                        _logger.info("     - Unit Price: %s", rfq_line.price_unit)
                                        # Get taxes for logging (try both field names)
                                        taxes = getattr(rfq_line, 'tax_ids', None) or getattr(rfq_line, 'taxes_id', None)
                                        tax_names = ', '.join(taxes.mapped('name')) if taxes else 'None'
                                        _logger.info("     - Taxes: %s", tax_names)
                                        _logger.info("     - Amount: %s (Qty: %s × Price: %s)", 
                                                   rfq_line.product_qty * rfq_line.price_unit,
                                                   rfq_line.product_qty,
                                                   rfq_line.price_unit)
                                        
                                        # Commit after each line
                                        self.env.cr.commit()
                                        
                                        # Invalidate cache
                                        rfq.invalidate_recordset(['order_line'])
                                        
                                        lines_created += 1
                                        _logger.info("  ✅ Migrated purchase order line %s (%s/%s) for RFQ %s", 
                                                   line_id, lines_created, len(line_ids), self.uploaded_rfq_number)
                                            
                                    except Exception as line_error:
                                        import traceback
                                        _logger.error("  " + "="*70)
                                        _logger.error("  ❌ CRITICAL ERROR: Failed to create line %s", line_id)
                                        _logger.error("  ❌ Error type: %s", type(line_error).__name__)
                                        _logger.error("  ❌ Error message: %s", str(line_error))
                                        _logger.error("  ❌ Full traceback:")
                                        _logger.error(traceback.format_exc())
                                        _logger.error("  " + "="*70)
                                        lines_failed += 1
                                        continue
                                else:
                                    _logger.warning("  ⚠️ Purchase order line %s not found in Odoo 14", line_id)
                                    lines_failed += 1
                            except Exception as e:
                                _logger.error("  ❌ Could not migrate purchase order line %s: %s", 
                                            line_id, str(e), exc_info=True)
                                lines_failed += 1
                                continue
                        
                        _logger.info("📊 Purchase order lines migration summary for RFQ %s: %s created, %s failed", 
                                    self.uploaded_rfq_number, lines_created, lines_failed)
                        
                        if lines_created == 0:
                            _logger.warning("⚠️ No purchase order lines were migrated for RFQ %s", self.uploaded_rfq_number)
                    except Exception as e:
                        _logger.error("❌ Error migrating purchase order lines: %s", str(e), exc_info=True)
                else:
                    _logger.warning("⚠️ No valid line IDs extracted from order_line for RFQ %s. Raw data: %s", 
                                  self.uploaded_rfq_number, order_line_ids)
            else:
                _logger.warning("⚠️ No order_line data found for RFQ %s", self.uploaded_rfq_number)
            
            # Verify lines were created - Refresh RFQ first
            rfq.invalidate_recordset(['order_line'])
            created_lines_count = len(rfq.order_line)
            _logger.info("📊 Final check: RFQ %s has %s order lines created", 
                        self.uploaded_rfq_number, created_lines_count)
            
            # Also check directly in database
            self.env.cr.execute("SELECT COUNT(*) FROM purchase_order_line WHERE order_id = %s", (rfq.id,))
            db_line_count = self.env.cr.fetchone()[0]
            _logger.info("📊 Database check: RFQ %s has %s order lines in database", 
                        self.uploaded_rfq_number, db_line_count)
            
            if created_lines_count == 0 and db_line_count == 0:
                _logger.error("❌ CRITICAL: RFQ %s was created but has NO order lines in memory or database!", 
                            self.uploaded_rfq_number)
                _logger.error("❌ Check logs above to see why lines were not created!")
            elif created_lines_count == 0 and db_line_count > 0:
                _logger.warning("⚠️ WARNING: RFQ %s has %s lines in database but 0 in memory. Cache issue?", 
                              self.uploaded_rfq_number, db_line_count)
                # Force reload
                rfq = self.env['purchase.order'].browse(rfq.id)
                _logger.info("📊 After reload: RFQ %s has %s order lines", 
                           self.uploaded_rfq_number, len(rfq.order_line))
            
            # Mark as migrated
            self.write({
                'status': 'migrated',
                'status_message': 'Successfully migrated',
                'odoo19_rfq_id': rfq.id,
                'in_system_rfq_number': rfq.name,
                'migration_date': fields.Datetime.now(),
                'error_message': False,
            })
            self.env.cr.commit()
            
            _logger.info("✅ Successfully migrated RFQ %s (Odoo 14 ID: %s -> Odoo 19 ID: %s)", 
                        self.uploaded_rfq_number, rfq_data['id'], rfq.id)
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'rfq.migration.line',
                'view_mode': 'list,form',
                'target': 'current',
            }
            
        except UserError:
            raise
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error migrating RFQ %s: %s", self.uploaded_rfq_number, error_msg, exc_info=True)
            _log_failed_rfq_migration(self.uploaded_rfq_number, error_msg)
            
            self.write({
                'status': 'error',
                'status_message': f'Error: {error_msg[:200]}',
                'error_message': error_msg,
            })
            self.env.cr.commit()
            raise UserError(f'Error migrating RFQ: {error_msg}')
    
    @api.model
    def _migrate_sequential(self, record_ids, current_index):
        """Sequentially migrate RFQs using queue jobs"""
        if current_index >= len(record_ids):
            _logger.info("✅ Completed sequential migration of %s RFQs", len(record_ids))
            return
        
        record = self.browse(record_ids[current_index])
        if not record.exists():
            _logger.warning("Record %s no longer exists, skipping", record_ids[current_index])
            # Continue with next record
            if current_index + 1 < len(record_ids):
                self.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        rfq_number = record.uploaded_rfq_number
        _logger.info("🔄 Migrating RFQ %s (%s/%s)", rfq_number, current_index + 1, len(record_ids))
        
        try:
            # Update status to migrating
            record.write({
                'status': 'migrating',
                'status_message': f'Migrating... ({current_index + 1}/{len(record_ids)})',
            })
            self.env.cr.commit()
            
            # Migrate this RFQ
            record.action_migrate()
            
            _logger.info("✅ Successfully migrated RFQ %s", rfq_number)
            
        except Exception as e:
            error_msg = str(e)
            _logger.error("❌ Error migrating RFQ %s: %s", rfq_number, error_msg, exc_info=True)
            _log_failed_rfq_migration(rfq_number, error_msg)
            
            record.write({
                'status': 'error',
                'status_message': f'Error: {error_msg[:200]}',
                'error_message': error_msg,
            })
            self.env.cr.commit()
        
        # Process next record
        if current_index + 1 < len(record_ids):
            self.with_delay()._migrate_sequential(record_ids, current_index + 1)

