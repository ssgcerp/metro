# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


def _log_failed_quotation_migration(quotation_number, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        # Get log directory (use module directory/logs)
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_quotation_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {quotation_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed quotation migration logged to: %s", log_file)
    except Exception as e:
        _logger.warning("Could not write to failed migrations log: %s", str(e))

# Check if queue_job is available
# Note: In Odoo 19, the @job decorator is obsolete - methods called via with_delay() 
# are automatically handled by queue_job without needing the decorator
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


class QuotationMigrationLine(models.Model):
    """Model to store uploaded quotation numbers and track migration status"""
    _name = 'eq.migration.quotation'
    _description = 'Quotation Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    uploaded_quotation_number = fields.Char(
        string='Uploaded Quotation Number',
        required=True,
        index=True,
        help='Quotation number from Excel upload'
    )
    
    in_system_quotation_number = fields.Char(
        string='In-System Quotation Number',
        readonly=True,
        help='Actual quotation number found in Odoo 14 or Odoo 19'
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
    
    odoo14_quotation_id = fields.Integer(
        string='Odoo 14 Quotation ID',
        readonly=True,
        help='ID of quotation in Odoo 14 if found'
    )
    
    odoo19_quotation_id = fields.Many2one(
        'sale.order',
        string='Odoo 19 Quotation',
        readonly=True,
        help='Migrated quotation in Odoo 19'
    )
    
    migration_date = fields.Datetime(string='Migration Date', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    def check_status(self, quotation_number=None, config_id=None):
        """Check status of a quotation number against Odoo 14 and Odoo 19"""
        self.ensure_one()
        if not quotation_number:
            quotation_number = self.uploaded_quotation_number
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
            existing_19 = self.env['sale.order'].search([
                ('name', '=', quotation_number)
            ], limit=1)
            
            if existing_19:
                return {
                    'status': 'already_migrated',
                    'message': 'Already exists in Odoo 19',
                    'odoo19_id': existing_19.id,
                    'odoo19_name': existing_19.name
                }
            
            # Check in Odoo 14
            quotations = client.search_read(
                'sale.order',
                [('name', '=', quotation_number)],
                ['id', 'name'],
                limit=1
            )
            
            if quotations:
                return {
                    'status': 'pending_migration',
                    'message': 'Found in Odoo 14, ready to migrate',
                    'odoo14_id': quotations[0]['id'],
                    'odoo14_name': quotations[0]['name']
                }
            else:
                return {
                    'status': 'not_found',
                    'message': 'Not found in Odoo 14'
                }
                
        except Exception as e:
            _logger.error("Error checking quotation status: %s", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def action_check_status(self):
        """Button action to refresh status"""
        for record in self:
            result = record.check_status()
            record.write({
                'status': result.get('status', 'not_found'),
                'status_message': result.get('message', ''),
                'in_system_quotation_number': result.get('odoo14_name') or result.get('odoo19_name') or '',
                'odoo14_quotation_id': result.get('odoo14_id', 0),
                'odoo19_quotation_id': result.get('odoo19_id', False),
            })
    
    @api.model
    def action_open_upload_wizard(self):
        """Open the Excel upload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'eq.quotation.upload.wizard',
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
            failed_jobs = self.env['queue.job'].search_count([('state', '=', 'failed')])
            done_jobs = self.env['queue.job'].search_count([('state', '=', 'done')])
            
            # Check for migration-specific jobs
            migration_pending = self.env['queue.job'].search_count([
                ('state', '=', 'pending'),
                ('model_name', '=', 'eq.migration.quotation'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            migration_started = self.env['queue.job'].search_count([
                ('state', '=', 'started'),
                ('model_name', '=', 'eq.migration.quotation'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            
            _logger.info("📊 Queue status: %s pending (total), %s started (total), %s migration pending, %s migration started", 
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
            
            # Try to find the cron job by XML ID first
            cron_job = None
            try:
                cron_job = self.env.ref('queue_job_cron_jobrunner.queue_job_cron', raise_if_not_found=False)
            except:
                pass
            
            # If not found by XML ID, search by queue_job_runner flag
            if not cron_job:
                cron_job = self.env['ir.cron'].sudo().search([
                    ('queue_job_runner', '=', True)
                ], limit=1)
            
            # If still not found, try to create it manually
            if not cron_job:
                # Try to create the cron job manually
                queue_job_model_id = self.env['ir.model'].search([('model', '=', 'queue.job')], limit=1)
                if queue_job_model_id:
                    cron_job = self.env['ir.cron'].sudo().create({
                        'name': 'Queue Job Runner',
                        'model_id': queue_job_model_id.id,
                        'state': 'code',
                        'code': 'model._job_runner()',
                        'queue_job_runner': True,
                        'user_id': self.env.ref('base.user_root').id,
                        'interval_number': 1,
                        'interval_type': 'minutes',
                        'active': True,
                    })
                    _logger.info("Created Queue Job Runner cron manually")
            
            if cron_job:
                # Trigger the cron job directly
                cron_job._trigger()
                if migration_pending > 0:
                    message = f'Queue job cron triggered successfully. {pending_jobs} pending job(s) (including {migration_pending} migration jobs) will start processing now.'
                else:
                    message = f'Queue job cron triggered successfully. {pending_jobs} pending job(s) will start processing now.'
            else:
                # Try method 2: Use _cron_trigger if available (from queue_job_cron_jobrunner)
                queue_job_model = self.env['queue.job']
                if hasattr(queue_job_model, '_cron_trigger'):
                    try:
                        queue_job_model._cron_trigger()
                        message = f'Queue job runner triggered successfully. {pending_jobs} pending job(s) will start processing now.'
                    except Exception as e:
                        _logger.error("Error calling _cron_trigger: %s", str(e), exc_info=True)
                        raise UserError(
                            f'Error triggering queue job runner: {str(e)}\n\n'
                            'Please:\n'
                            '1. Upgrade "queue_job_cron_jobrunner" module\n'
                            '2. Restart Odoo server'
                        )
                else:
                    raise UserError(
                        'Queue Job Cron Jobrunner cron job not found.\n\n'
                        'Please:\n'
                        '1. Upgrade "queue_job_cron_jobrunner" module\n'
                        '2. Restart Odoo server\n'
                        '3. Or manually create the cron job in Settings → Technical → Automation → Scheduled Actions\n\n'
                        f'Currently {pending_jobs} job(s) are pending in the queue.'
                    )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Queue Job Runner Triggered',
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error triggering queue job runner: %s", str(e), exc_info=True)
            raise UserError(
                f'Error triggering queue job runner: {str(e)}\n\n'
                'Please check:\n'
                '1. queue_job module is installed\n'
                '2. queue_job_cron_jobrunner module is installed\n'
                '3. Both modules are upgraded\n'
                '4. Odoo server is restarted'
            )
    
    def action_bulk_migrate(self):
        """Bulk migrate selected quotations sequentially using Queue Jobs"""
        # Wrap entire method to ensure we never leave records in 'error' status
        try:
            pending = self.filtered(lambda l: l.status == 'pending_migration')
            if not pending:
                raise UserError('No quotations with "Pending Migration" status selected')
            
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
                raise UserError('No quotations with "Pending Migration" status selected')
            
            # Mark all records as "queued" - user will start the migration process separately
            # Use fresh recordset to ensure we're working with the latest data
            fresh_pending = self.env['eq.migration.quotation'].browse(pending_ids)
            for record in fresh_pending:
                record.write({
                    'status': 'queued',
                    'status_message': 'Queued for migration - waiting to be processed',
                    'error_message': False,  # Clear any previous error messages
                })
            self.env.cr.commit()
            _logger.info("✅ Marked %s quotations as 'queued' (ready for processing)", len(fresh_pending))
        
            # Return success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Quotations Queued',
                    'message': f'{len(pending_ids)} quotations have been queued. Use "Process Queue Jobs Now" to start the migration process.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except UserError as ue:
            # For UserError, try to keep status as queued if possible
            # Only revert if we haven't set status to queued yet
            if 'fresh_pending' in locals() and fresh_pending:
                try:
                    # Check if status was already set to queued
                    current_status = fresh_pending[0].status if fresh_pending else None
                    if current_status != 'queued':
                        # Status wasn't set yet, so this is an early error - re-raise
                        raise
                    else:
                        # Status is already queued, keep it and show warning
                        fresh_pending.write({
                            'status': 'queued',
                            'status_message': f'Queued - validation issue: {str(ue)[:200]}',
                            'error_message': str(ue),
                        })
                        self.env.cr.commit()
                        # Show warning instead of error
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Quotations Queued (with warnings)',
                                'message': f'{len(fresh_pending)} quotations queued, but there were some issues. Check status messages for details.',
                                'type': 'warning',
                                'sticky': False,
                            }
                        }
                except:
                    # If we can't update, just re-raise the original error
                    raise ue
            else:
                # No fresh_pending yet, re-raise the error
                raise ue
        except Exception as e:
            # Catch any unexpected errors - try to keep status as queued
            error_msg = str(e)
            error_type = type(e).__name__
            _logger.warning("Unexpected error in action_bulk_migrate (%s): %s", error_type, error_msg, exc_info=True)
            
            # Try to ensure status stays as queued
            try:
                if 'pending_ids' in locals() and pending_ids:
                    fresh_pending = self.env['eq.migration.quotation'].browse(pending_ids)
                    # Set or keep status as queued
                    fresh_pending.write({
                        'status': 'queued',  # Keep as queued, don't revert
                        'status_message': f'Queued - unexpected error occurred: {error_msg[:200]}',
                        'error_message': error_msg[:500],
                    })
                    self.env.cr.commit()
                    
                    # Return success notification anyway
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Quotations Queued',
                            'message': f'{len(pending_ids)} quotations have been queued. There were some issues during enqueueing - check status messages for details.',
                            'type': 'warning',
                            'sticky': False,
                        }
                    }
            except Exception as revert_error:
                _logger.error("Failed to set status after unexpected error: %s", str(revert_error))
            
            # If we can't set status, still don't raise error - let user see what happened
            # But log it as a warning, not an error
            _logger.warning("Could not set queued status, but continuing anyway")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Action Completed',
                    'message': f'Action completed, but there were some issues. Please check the quotation records.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
    
    def action_start_queued_migration(self):
        """Start processing queued quotations - enqueue the first job to start sequential migration"""
        queued = self.filtered(lambda l: l.status == 'queued')
        if not queued:
            raise UserError('No quotations with "Queued" status selected')
        
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
            raise UserError('No quotations with "Queued" status selected')
        
        # Start sequential migration by enqueueing the first job
        try:
            first_record = self.browse(queued_ids[0])
            if not first_record.exists():
                raise UserError(f'Record {queued_ids[0]} no longer exists')
            
            # Enqueue the first job - it will automatically process the rest sequentially
            job = first_record.with_delay()._migrate_sequential(queued_ids, 0)
            
            _logger.info("✅ Started sequential migration for %s queued quotations (job UUID: %s)", 
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
                    'message': f'Started processing {len(queued_ids)} queued quotations. Migration will continue sequentially.',
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
        """Migrate this quotation from Odoo 14 to Odoo 19"""
        self.ensure_one()
        
        if self.status not in ('pending_migration', 'queued'):
            raise UserError('Can only migrate quotations with "Pending Migration" or "Queued" status')
        
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
            
            # Get initial quotation data from Odoo 14 (use minimal safe fields only)
            # NEVER use empty fields list [] - it tries to read ALL fields including computed ones
            safe_initial_fields = ['id', 'name']  # Minimal fields to find the quotation
            quotations = client.search_read(
                'sale.order',
                [('name', '=', self.uploaded_quotation_number)],
                safe_initial_fields,  # Use explicit safe fields, never []
                limit=1
            )
            
            if not quotations:
                self.write({
                    'status': 'not_found',
                    'status_message': 'Quotation not found in Odoo 14',
                })
                return
            
            quotation_data = quotations[0]
            
            # Use existing migration wizard logic
            wizard = self.env['odoo14.customer.migration.wizard'].create({
                'config_id': self.config_id.id,
            })
            
            # Get fields to fetch - ONLY stored fields, NEVER computed accounting fields
            # Fields to exclude (computed fields that cause errors in XML-RPC)
            excluded_fields = [
                'due_amount', 'credit', 'debit', 'partner_credit', 'partner_debit',
                'invoice_ids', 'invoice_count', 'invoice_status', 'invoice_pending',
                'invoice_shipped_pending_sum', 'invoice_shipped_pending_count', 'invoice_shipped_pending_rate',
                'invoice_shipped_sum', 'invoice_shipped_count', 'invoice_shipped_rate',
                'invoice_delivered_sum', 'invoice_delivered_count', 'invoice_delivered_rate',
                'invoice_done_sum', 'invoice_done_count', 'invoice_done_rate',
                'invoice_partially_sum', 'invoice_partially_count', 'invoice_partially_rate',
                'invoice_not_sum', 'invoice_not_count', 'invoice_not_rate',
            ]
            
            # Safe stored fields only - NEVER include computed accounting fields
            # Start with minimal safe fields
            fields_to_fetch = [
                'id', 'name', 'partner_id', 'date_order', 'validity_date', 'amount_total',
                'amount_untaxed', 'amount_tax', 'state', 'pricelist_id', 'payment_term_id',
                'order_line', 'note', 'client_order_ref', 'user_id', 'team_id', 'company_id', 
                'create_date', 'write_date', 'write_uid', 'create_uid'
            ]
            
            # Initialize estimation_fields list (will be populated if fields exist and are verified)
            estimation_fields = []
            estimation_field_names = ['estimation_id', 'crm_estimation_id', 'estimation', 'crm_estimation']
            
            # Try to add more stored fields, but be very careful
            # NOTE: We do NOT add estimation fields here - they are handled separately after verification
            try:
                all_fields = client.fields_get('sale.order')
                if all_fields:
                    dynamic_fields = []
                    # Check if estimation fields exist - but DON'T add them yet
                    # We'll verify they can actually be read before adding them
                    for est_field in estimation_field_names:
                        if est_field in all_fields:
                            field_info = all_fields[est_field]
                            field_store = field_info.get('store', True)
                            field_type = field_info.get('type', '')
                            # Only mark for potential addition if it's a stored many2one field
                            # But we won't add it until we verify it can be read
                            if field_store and field_type == 'many2one':
                                estimation_fields.append(est_field)
                                _logger.debug("Found potential estimation field in fields_get: %s", est_field)
                    
                    if not estimation_fields:
                        _logger.info("No estimation fields found in Odoo 14 sale.order model")
                    
                    # Add other dynamic fields
                    for f, field_info in all_fields.items():
                        # Skip excluded fields
                        if f in excluded_fields:
                            continue
                        # Skip if already in fields_to_fetch
                        if f in fields_to_fetch:
                            continue
                        # Skip estimation fields (already handled above)
                        if f in ['estimation_id', 'crm_estimation_id', 'estimation', 'crm_estimation']:
                            continue
                        field_type = field_info.get('type', '')
                        field_store = field_info.get('store', True)
                        # CRITICAL: Skip computed fields (not stored) - these cause CacheMiss errors
                        if not field_store:
                            continue
                        # Skip one2many/many2many except order_line
                        if field_type in ('one2many', 'many2many') and f != 'order_line':
                            continue
                        # Only include simple stored fields
                        if field_type in ('char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime', 'many2one', 'selection'):
                            dynamic_fields.append(f)
                    fields_to_fetch = list(set(fields_to_fetch + dynamic_fields))
            except Exception as e:
                _logger.warning("Could not get all fields: %s", str(e))
                # Continue with safe default fields only
            
            # CRITICAL: Always remove estimation fields BEFORE any search_read call
            # fields_get() might report fields that don't actually exist or can't be read
            # Since we know these fields cause errors in Odoo 14, we'll remove them unconditionally
            # and only try to read them separately if needed for estimation linking
            
            # Remove ALL estimation fields from fields_to_fetch - they cause errors in Odoo 14
            fields_to_fetch = [f for f in fields_to_fetch if f not in estimation_field_names]
            _logger.info("Removed all estimation fields from fields_to_fetch to prevent XML-RPC errors")
            
            # Note: We'll check for estimation_id separately after fetching the quotation
            # by looking at the quotation data structure, not by requesting the field directly
            
            # Get full quotation data with safe fields only
            # CRITICAL: Always use explicit field list, NEVER empty list []
            # This prevents Odoo from trying to read computed accounting fields
            minimal_safe_fields = [
                'id', 'name', 'partner_id', 'date_order', 'validity_date', 'amount_total',
                'amount_untaxed', 'amount_tax', 'state', 'pricelist_id', 'payment_term_id',
                'order_line', 'note', 'client_order_ref', 'user_id', 'team_id', 'company_id', 
                'create_date', 'write_date'
                # Note: estimation fields are NOT included in minimal_safe_fields as they may not exist in Odoo 14
            ]
            
            try:
                # Try with expanded fields list
                full_quotation = client.search_read(
                    'sale.order',
                    [('id', '=', quotation_data['id'])],
                    fields_to_fetch,  # Use the filtered safe fields
                    limit=1
                )
            except Exception as e:
                error_msg = str(e)
                _logger.warning("Error fetching quotation with expanded fields: %s. Trying to fix and retry.", error_msg)
                
                # Check for "Invalid field" errors - extract field name from error
                problematic_fields = []
                if 'Invalid field' in error_msg:
                    # Try to extract field name from error message
                    import re
                    match = re.search(r"Invalid field ['\"]([^'\"]+)['\"]", error_msg)
                    if match:
                        problematic_field = match.group(1)
                        problematic_fields.append(problematic_field)
                        _logger.info("Detected invalid field: %s", problematic_field)
                
                # Also check for estimation-related errors
                if 'estimation' in error_msg.lower() or 'crm_estimation' in error_msg.lower():
                    problematic_fields.extend(['estimation_id', 'crm_estimation_id', 'estimation', 'crm_estimation'])
                    _logger.info("Removing estimation fields that don't exist in Odoo 14")
                
                # Remove problematic fields from fields_to_fetch and try again
                if problematic_fields:
                    safe_fields = [f for f in fields_to_fetch if f not in problematic_fields]
                    try:
                        full_quotation = client.search_read(
                            'sale.order',
                            [('id', '=', quotation_data['id'])],
                            safe_fields,
                            limit=1
                        )
                        _logger.info("Successfully fetched quotation with safe fields (removed problematic fields: %s)", problematic_fields)
                    except Exception as e2:
                        _logger.warning("Error with safe fields: %s. Using minimal safe fields.", str(e2))
                        # Final fallback: use minimal safe fields only (guaranteed to work)
                        full_quotation = client.search_read(
                            'sale.order',
                            [('id', '=', quotation_data['id'])],
                            minimal_safe_fields,  # Minimal guaranteed-safe fields
                            limit=1
                        )
                else:
                    # Fallback: use minimal safe fields only (guaranteed to work)
                    full_quotation = client.search_read(
                        'sale.order',
                        [('id', '=', quotation_data['id'])],
                        minimal_safe_fields,  # Minimal guaranteed-safe fields
                        limit=1
                    )
            
            if not full_quotation:
                raise UserError('Could not fetch full quotation data')
            
            quotation_data = full_quotation[0]
            
            # Try to get estimation_id separately using direct read() call
            # This might work even if search_read fails with the field
            estimation_id = None
            quotation_odoo14_id = quotation_data.get('id')
            if quotation_odoo14_id:
                try:
                    # Try to read estimation_id directly from the sale.order record
                    estimation_fields_to_try = ['estimation_id', 'crm_estimation_id', 'estimation', 'crm_estimation']
                    for est_field in estimation_fields_to_try:
                        try:
                            estimation_read = client.read('sale.order', [quotation_odoo14_id], [est_field])
                            if estimation_read and len(estimation_read) > 0:
                                est_value = estimation_read[0].get(est_field)
                                if est_value:
                                    estimation_id = est_value
                                    _logger.info("✅ Found estimation_id %s using field %s for quotation %s", 
                                               estimation_id, est_field, self.uploaded_quotation_number)
                                    break
                        except Exception as e:
                            error_msg = str(e).lower()
                            # If field doesn't exist, that's fine - try next field
                            if 'invalid field' in error_msg or "doesn't exist" in error_msg:
                                _logger.debug("Field %s doesn't exist in Odoo 14: %s", est_field, str(e))
                            else:
                                _logger.debug("Could not read field %s: %s", est_field, str(e))
                            continue
                except Exception as e:
                    _logger.debug("Could not read estimation fields directly: %s", str(e))
            
            # Also check if estimation_id is in the quotation_data (might have been included)
            if not estimation_id:
                if 'estimation_id' in quotation_data:
                    estimation_id = quotation_data.get('estimation_id')
                elif 'crm_estimation_id' in quotation_data:
                    estimation_id = quotation_data.get('crm_estimation_id')
            
            # Fallback: Try to find estimation by matching quotation name pattern
            # Some Odoo 14 systems link quotations to estimations by name pattern
            # e.g., quotation "MFS/AUH/RW/01844/2025 R1" might link to estimation "MSF/AUH/EST/2025/1884"
            if not estimation_id:
                try:
                    quotation_name = self.uploaded_quotation_number
                    # Try to find estimation by similar name pattern
                    import re
                    # Extract parts from quotation name
                    # Example: "MFS/AUH/RW/01844/2025 R1" -> try "MSF/AUH/EST/2025/1884"
                    # Remove revision suffix (R1, R2, etc.)
                    quotation_name_clean = re.sub(r'\s+R\d+$', '', quotation_name)
                    parts = re.split(r'[/\s]', quotation_name_clean)
                    
                    if len(parts) >= 5:
                        # Format: MFS/AUH/RW/01844/2025
                        prefix = parts[0]  # MFS
                        branch = parts[1]  # AUH
                        number = parts[3]   # 01844
                        year = parts[4]     # 2025
                        
                        # Try to construct estimation number patterns
                        # Pattern variations based on common naming conventions
                        possible_estimation_patterns = []
                        
                        # Try: MSF/AUH/EST/2025/1884 (remove leading zeros, change prefix)
                        number_no_zeros = number.lstrip('0') or '0'
                        possible_estimation_patterns.append(f"MSF/{branch}/EST/{year}/{number_no_zeros}")
                        
                        # Try: MFS/AUH/EST/2025/1884 (keep prefix, remove leading zeros)
                        possible_estimation_patterns.append(f"{prefix}/{branch}/EST/{year}/{number_no_zeros}")
                        
                        # Try: MSF/AUH/EST/2025/01844 (keep leading zeros, change prefix)
                        possible_estimation_patterns.append(f"MSF/{branch}/EST/{year}/{number}")
                        
                        # Try: MFS/AUH/EST/2025/01844 (keep both)
                        possible_estimation_patterns.append(f"{prefix}/{branch}/EST/{year}/{number}")
                        
                        # Also try reversing number digits or other variations if needed
                        # Search for estimation in Odoo 19 by these patterns
                        for pattern in possible_estimation_patterns:
                            estimation_19 = self.env['fm.amc.estimation'].search([
                                ('name', '=', pattern)
                            ], limit=1)
                            if estimation_19:
                                _logger.info("✅ Found estimation %s by name pattern matching for quotation %s", 
                                           pattern, quotation_name)
                                # We'll link it later after creating the quotation
                                estimation_id = 'pattern_matched_' + str(estimation_19.id)
                                break
                except Exception as e:
                    _logger.debug("Could not try pattern matching for estimation: %s", str(e))
            
            # Check if quotation already exists in Odoo 19 BEFORE migrating (duplicate prevention)
            existing_quotation = self.env['sale.order'].search([
                ('name', '=', self.uploaded_quotation_number)
            ], limit=1)
            
            if existing_quotation:
                # Quotation already exists - mark as migrated
                _logger.info("Quotation %s already exists in Odoo 19 (ID: %s), marking as migrated", 
                           self.uploaded_quotation_number, existing_quotation.id)
                self.write({
                    'status': 'migrated',
                    'status_message': 'Already migrated (existed in system)',
                    'odoo19_quotation_id': existing_quotation.id,
                    'in_system_quotation_number': existing_quotation.name,
                    'migration_date': fields.Datetime.now(),
                    'error_message': False,
                })
                self.env.cr.commit()
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'eq.migration.quotation',
                    'view_mode': 'tree,form',
                    'target': 'current',
                }
            
            # Check for duplicate customer (if partner_id exists)
            partner_id = quotation_data.get('partner_id')
            if partner_id:
                partner_id_val = partner_id[0] if isinstance(partner_id, list) else partner_id
                if partner_id_val:
                    # Check if partner exists in Odoo 19
                    existing_partner = self.env['res.partner'].search([
                        ('id', '=', partner_id_val)
                    ], limit=1)
                    if not existing_partner:
                        # Partner doesn't exist - will be created during migration
                        pass
            
            # Update status to migrating
            self.write({
                'status': 'migrating',
                'status_message': 'Migration in progress...',
            })
            self.env.cr.commit()
            
            # Migrate using wizard's helper methods
            try:
                quotation_vals = wizard._prepare_quotation_vals(quotation_data, client)
                
                # Link estimation if we found one
                if estimation_id:
                    estimation_id_val = estimation_id[0] if isinstance(estimation_id, list) else estimation_id
                    if estimation_id_val:
                        try:
                            # Try to get estimation from Odoo 14
                            estimation_data_14 = client.search_read(
                                'crm.estimation',
                                [('id', '=', estimation_id_val)],
                                ['name'],
                                limit=1
                            )
                            if not estimation_data_14:
                                # Try alternative model names
                                for model_name in ['fm.amc.estimation', 'estimation.estimation']:
                                    try:
                                        estimation_data_14 = client.search_read(
                                            model_name,
                                            [('id', '=', estimation_id_val)],
                                            ['name'],
                                            limit=1
                                        )
                                        if estimation_data_14:
                                            break
                                    except:
                                        continue
                            
                            if estimation_data_14:
                                estimation_number = estimation_data_14[0].get('name')
                                if estimation_number:
                                    # Find estimation in Odoo 19 by number
                                    estimation_19 = self.env['fm.amc.estimation'].search([
                                        ('name', '=', estimation_number)
                                    ], limit=1)
                                    
                                    if estimation_19:
                                        # Set estimation checkbox and estimation_id
                                        # Check if sale.order has is_estimation field (checkbox)
                                        sale_order_fields = self.env['sale.order']._fields
                                        if 'is_estimation' in sale_order_fields:
                                            quotation_vals['is_estimation'] = True
                                            _logger.info("Set is_estimation checkbox to True for quotation %s", self.uploaded_quotation_number)
                                        
                                        # Set estimation_id if field exists (many2one field)
                                        if 'estimation_id' in sale_order_fields:
                                            quotation_vals['estimation_id'] = estimation_19.id
                                            _logger.info("Set estimation_id to %s (%s) for quotation %s", 
                                                       estimation_19.id, estimation_number, self.uploaded_quotation_number)
                                        
                                        _logger.info("✅ Successfully linked estimation %s (ID: %s) to quotation %s", 
                                                   estimation_number, estimation_19.id, self.uploaded_quotation_number)
                                    else:
                                        _logger.warning("Estimation %s not found in Odoo 19 for quotation %s", estimation_number, self.uploaded_quotation_number)
                                else:
                                    _logger.warning("Estimation number not found in Odoo 14 data for quotation %s", self.uploaded_quotation_number)
                            else:
                                _logger.warning("Estimation data not found in Odoo 14 for ID %s (quotation %s)", estimation_id_val, self.uploaded_quotation_number)
                        except Exception as e:
                            _logger.warning("Could not link estimation to quotation %s: %s", self.uploaded_quotation_number, str(e))
                
                quotation = self.env['sale.order'].create(quotation_vals)
                
                # Preserve original creation date
                src_create_date = quotation_data.get('create_date')
                if src_create_date:
                    try:
                        self.env.cr.execute(
                            """
                            UPDATE sale_order
                               SET create_date = %s,
                                   write_date = COALESCE(write_date, %s)
                             WHERE id = %s
                            """,
                            (src_create_date, src_create_date, quotation.id),
                        )
                    except Exception as e:
                        _logger.warning("Could not set original create_date: %s", str(e))
                
                wizard._create_quotation_lines(quotation, quotation_data, client)
                self.env.cr.commit()
                
                # Update status to migrated
                self.write({
                    'status': 'migrated',
                    'status_message': 'Successfully migrated',
                    'odoo19_quotation_id': quotation.id,
                    'in_system_quotation_number': quotation.name,
                    'migration_date': fields.Datetime.now(),
                    'error_message': False,
                })
                self.env.cr.commit()
                
                # Return to reload list view
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'eq.migration.quotation',
                    'view_mode': 'tree,form',
                    'target': 'current',
                }
                
            except Exception as e:
                error_msg = str(e)
                _logger.error("Error migrating quotation %s: %s", self.uploaded_quotation_number, error_msg)
                self.write({
                    'status': 'error',
                    'status_message': 'Migration failed',
                    'error_message': error_msg,
                })
                self.env.cr.commit()
                # Log failed migration for later processing
                _log_failed_quotation_migration(self.uploaded_quotation_number, error_msg)
                raise UserError('Migration failed: %s' % error_msg)
                
        except UserError:
            raise
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error in action_migrate: %s", error_msg)
            self.write({
                'status': 'error',
                'status_message': 'Error: %s' % error_msg,
                'error_message': error_msg,
            })
            self.env.cr.commit()
            # Log failed migration for later processing
            _log_failed_quotation_migration(self.uploaded_quotation_number, error_msg)
            raise UserError('Error migrating quotation: %s' % str(e))
    
    def _migrate_sequential(self, record_ids, current_index):
        """
        Sequential migration method using Queue Jobs.
        Migrates one quotation at a time, updates status, sends notification, then starts next.
        
        :param record_ids: List of record IDs to migrate
        :param current_index: Current index in the list (0-based)
        """
        if current_index >= len(record_ids):
            _logger.info("Sequential migration completed for all %s records", len(record_ids))
            return
        
        record_id = record_ids[current_index]
        # Use environment to get fresh recordset (important in queue job context)
        record = self.env['eq.migration.quotation'].browse(record_id)
        
        if not record.exists():
            _logger.warning("Record %s does not exist, skipping", record_id)
            # Continue with next record
            if current_index + 1 < len(record_ids):
                next_record = record.env['eq.migration.quotation'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        quotation_number = record.uploaded_quotation_number
        _logger.info("🚀 Starting migration %s/%s: %s (record_id=%s)", current_index + 1, len(record_ids), quotation_number, record_id)
        
        # Accept both 'pending_migration' and 'queued' status
        if record.status not in ('pending_migration', 'queued'):
            _logger.warning("Record %s is not in pending_migration or queued status (%s), skipping", quotation_number, record.status)
            # Continue with next
            if current_index + 1 < len(record_ids):
                next_record = record.env['eq.migration.quotation'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        if not record.config_id:
            record.write({
                'status': 'error',
                'status_message': 'Migration configuration is required',
                'error_message': 'Migration configuration is required',
            })
            record.env.flush_all()  # Flush instead of commit to avoid breaking savepoint
            
            # Send notification
            self._send_migration_notification(record, 'error', 'Configuration missing')
            
            # Continue with next
            if current_index + 1 < len(record_ids):
                next_record = record.env['eq.migration.quotation'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        # Update status to migrating BEFORE starting migration
        record.write({
            'status': 'migrating',
            'status_message': 'Migration in progress...',
        })
        record.env.flush_all()  # Flush instead of commit to avoid breaking savepoint
        _logger.info("📝 Status updated to 'migrating' for %s", quotation_number)
        
        # Wrap entire migration in try-except to ensure we always continue to next job
        try:
            _logger.info("📡 Connecting to Odoo 14 for %s...", quotation_number)
            
            # Perform migration (reuse existing logic)
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=record.config_id.odoo14_url,
                db=record.config_id.odoo14_database,
                username=record.config_id.odoo14_username,
                password=record.config_id.odoo14_password
            )
            
            _logger.info("🔐 Authenticating with Odoo 14...")
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14')
            _logger.info("✅ Authenticated successfully")
            
            # Get quotation data
            _logger.info("🔍 Searching for quotation %s in Odoo 14...", quotation_number)
            safe_initial_fields = ['id', 'name']
            quotations = client.search_read(
                'sale.order',
                [('name', '=', quotation_number)],
                safe_initial_fields,
                limit=1
            )
            _logger.info("📋 Found %s quotation(s) in Odoo 14", len(quotations))
            
            if not quotations:
                record.write({
                    'status': 'not_found',
                    'status_message': 'Quotation not found in Odoo 14',
                })
                record.env.flush_all()  # Flush instead of commit to avoid breaking savepoint
                self._send_migration_notification(record, 'not_found', 'Not found in Odoo 14')
                
                # Continue with next
                if current_index + 1 < len(record_ids):
                    next_record = record.env['eq.migration.quotation'].browse(record_ids[current_index + 1])
                    if next_record.exists():
                        next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
                return
            
            quotation_data = quotations[0]
            _logger.info("📦 Quotation ID in Odoo 14: %s", quotation_data.get('id'))
            
            # Use existing migration wizard logic
            _logger.info("🔧 Creating migration wizard...")
            wizard = record.env['odoo14.customer.migration.wizard'].create({
                'config_id': record.config_id.id,
            })
            
            # Get fields to fetch (same logic as action_migrate)
            _logger.info("📋 Fetching quotation fields...")
            excluded_fields = [
                'due_amount', 'credit', 'debit', 'partner_credit', 'partner_debit',
                'invoice_ids', 'invoice_count', 'invoice_status', 'invoice_pending',
                'invoice_shipped_pending_sum', 'invoice_shipped_pending_count', 'invoice_shipped_pending_rate',
                'invoice_shipped_sum', 'invoice_shipped_count', 'invoice_shipped_rate',
                'invoice_delivered_sum', 'invoice_delivered_count', 'invoice_delivered_rate',
                'invoice_done_sum', 'invoice_done_count', 'invoice_done_rate',
                'invoice_partially_sum', 'invoice_partially_count', 'invoice_partially_rate',
                'invoice_not_sum', 'invoice_not_count', 'invoice_not_rate',
            ]
            
            fields_to_fetch = [
                'id', 'name', 'partner_id', 'date_order', 'validity_date', 'amount_total',
                'amount_untaxed', 'amount_tax', 'state', 'pricelist_id', 'payment_term_id',
                'order_line', 'note', 'client_order_ref', 'user_id', 'team_id', 'company_id', 
                'create_date', 'write_date', 'write_uid', 'create_uid'
            ]
            
            # Initialize estimation_fields list (for reference only - we won't use them)
            estimation_fields = []
            estimation_field_names = ['estimation_id', 'crm_estimation_id', 'estimation', 'crm_estimation']
            
            try:
                all_fields = client.fields_get('sale.order')
                if all_fields:
                    dynamic_fields = []
                    # Check if estimation fields exist - but DON'T add them
                    # We know they cause errors in Odoo 14, so we'll never fetch them
                    for est_field in estimation_field_names:
                        if est_field in all_fields:
                            field_info = all_fields[est_field]
                            field_store = field_info.get('store', True)
                            field_type = field_info.get('type', '')
                            if field_store and field_type == 'many2one':
                                estimation_fields.append(est_field)
                                _logger.debug("Found potential estimation field in fields_get: %s (but won't fetch it)", est_field)
                    
                    if not estimation_fields:
                        _logger.info("No estimation fields found in Odoo 14 sale.order model")
                    
                    # Add other dynamic fields
                    for f, field_info in all_fields.items():
                        if f in excluded_fields or f in fields_to_fetch:
                            continue
                        # Skip estimation fields (we never fetch them)
                        if f in estimation_field_names:
                            continue
                        field_type = field_info.get('type', '')
                        field_store = field_info.get('store', True)
                        if not field_store:
                            continue
                        if field_type in ('one2many', 'many2many') and f != 'order_line':
                            continue
                        if field_type in ('char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime', 'many2one', 'selection'):
                            dynamic_fields.append(f)
                    fields_to_fetch = list(set(fields_to_fetch + dynamic_fields))
            except Exception as e:
                _logger.warning("Could not get all fields: %s", str(e))
            
            # CRITICAL: Always remove estimation fields BEFORE any search_read call
            # These fields cause XML-RPC errors in Odoo 14, so we remove them unconditionally
            fields_to_fetch = [f for f in fields_to_fetch if f not in estimation_field_names]
            _logger.info("Removed all estimation fields from fields_to_fetch to prevent XML-RPC errors")
            
            minimal_safe_fields = [
                'id', 'name', 'partner_id', 'date_order', 'validity_date', 'amount_total',
                'amount_untaxed', 'amount_tax', 'state', 'pricelist_id', 'payment_term_id',
                'order_line', 'note', 'client_order_ref', 'user_id', 'team_id', 'company_id', 
                'create_date', 'write_date'
                # Note: estimation fields are NOT included in minimal_safe_fields as they may not exist in Odoo 14
            ]
            
            try:
                full_quotation = client.search_read(
                    'sale.order',
                    [('id', '=', quotation_data['id'])],
                    fields_to_fetch,
                    limit=1
                )
            except Exception as e:
                error_msg = str(e)
                _logger.warning("Error fetching quotation with expanded fields: %s. Trying to fix and retry.", error_msg)
                
                # Check for "Invalid field" errors - extract field name from error
                problematic_fields = []
                if 'Invalid field' in error_msg:
                    # Try to extract field name from error message
                    import re
                    match = re.search(r"Invalid field ['\"]([^'\"]+)['\"]", error_msg)
                    if match:
                        problematic_field = match.group(1)
                        problematic_fields.append(problematic_field)
                        _logger.info("Detected invalid field: %s", problematic_field)
                
                # Also check for estimation-related errors
                if 'estimation' in error_msg.lower() or 'crm_estimation' in error_msg.lower():
                    problematic_fields.extend(['estimation_id', 'crm_estimation_id', 'estimation', 'crm_estimation'])
                    _logger.info("Removing estimation fields that don't exist in Odoo 14")
                
                # Remove problematic fields from fields_to_fetch and try again
                if problematic_fields:
                    safe_fields = [f for f in fields_to_fetch if f not in problematic_fields]
                    try:
                        full_quotation = client.search_read(
                            'sale.order',
                            [('id', '=', quotation_data['id'])],
                            safe_fields,
                            limit=1
                        )
                        _logger.info("Successfully fetched quotation with safe fields (without estimation fields)")
                    except Exception as e2:
                        _logger.warning("Error with safe fields: %s. Using minimal safe fields.", str(e2))
                        # Final fallback: use minimal safe fields only (guaranteed to work)
                        full_quotation = client.search_read(
                            'sale.order',
                            [('id', '=', quotation_data['id'])],
                            minimal_safe_fields,
                            limit=1
                        )
                else:
                    # Fallback: use minimal safe fields only (guaranteed to work)
                    full_quotation = client.search_read(
                        'sale.order',
                        [('id', '=', quotation_data['id'])],
                        minimal_safe_fields,
                        limit=1
                    )
            
            if not full_quotation:
                raise UserError('Could not fetch full quotation data')
            
            quotation_data = full_quotation[0]
            _logger.info("✅ Fetched full quotation data for %s", quotation_number)
            
            # Try to get estimation_id separately using direct read() call
            # This might work even if search_read fails with the field
            estimation_id = None
            quotation_odoo14_id = quotation_data.get('id')
            if quotation_odoo14_id:
                try:
                    # Try to read estimation_id directly from the sale.order record
                    estimation_fields_to_try = ['estimation_id', 'crm_estimation_id', 'estimation', 'crm_estimation']
                    for est_field in estimation_fields_to_try:
                        try:
                            estimation_read = client.read('sale.order', [quotation_odoo14_id], [est_field])
                            if estimation_read and len(estimation_read) > 0:
                                est_value = estimation_read[0].get(est_field)
                                if est_value:
                                    estimation_id = est_value
                                    _logger.info("✅ Found estimation_id %s using field %s for quotation %s", 
                                               estimation_id, est_field, quotation_number)
                                    break
                        except Exception as e:
                            error_msg = str(e).lower()
                            # If field doesn't exist, that's fine - try next field
                            if 'invalid field' in error_msg or "doesn't exist" in error_msg:
                                _logger.debug("Field %s doesn't exist in Odoo 14: %s", est_field, str(e))
                            else:
                                _logger.debug("Could not read field %s: %s", est_field, str(e))
                            continue
                except Exception as e:
                    _logger.debug("Could not read estimation fields directly: %s", str(e))
            
            # Also check if estimation_id is in the quotation_data (might have been included)
            if not estimation_id:
                if 'estimation_id' in quotation_data:
                    estimation_id = quotation_data.get('estimation_id')
                elif 'crm_estimation_id' in quotation_data:
                    estimation_id = quotation_data.get('crm_estimation_id')
            
            # Fallback: Try to find estimation by matching quotation name pattern
            # Some Odoo 14 systems link quotations to estimations by name pattern
            if not estimation_id:
                try:
                    # Try to find estimation by similar name pattern
                    import re
                    parts = re.split(r'[/\s]', quotation_number)
                    if len(parts) >= 4:
                        possible_estimation_patterns = []
                        if len(parts) >= 5:
                            prefix = parts[0]  # MFS
                            branch = parts[1]  # AUH
                            number = parts[3]   # 01844
                            year = parts[4]     # 2025
                            # Try variations
                            possible_estimation_patterns.append(f"{prefix}/{branch}/EST/{year}/{number}")
                            possible_estimation_patterns.append(f"MSF/{branch}/EST/{year}/{number.lstrip('0')}")
                            possible_estimation_patterns.append(f"{prefix}/{branch}/EST/{year}/{number.lstrip('0')}")
                        
                        # Search for estimation in Odoo 19 by these patterns
                        for pattern in possible_estimation_patterns:
                            estimation_19 = record.env['fm.amc.estimation'].search([
                                ('name', '=', pattern)
                            ], limit=1)
                            if estimation_19:
                                _logger.info("Found estimation %s by name pattern matching for quotation %s", 
                                           pattern, quotation_number)
                                estimation_id = 'pattern_matched_' + str(estimation_19.id)
                                break
                except Exception as e:
                    _logger.debug("Could not try pattern matching for estimation: %s", str(e))
            
            # Migrate using wizard's helper methods
            _logger.info("🔄 Preparing quotation values...")
            quotation_vals = wizard._prepare_quotation_vals(quotation_data, client)
            
            # Link estimation if we found one
            if estimation_id:
                # Handle pattern-matched estimation (already found in Odoo 19)
                if isinstance(estimation_id, str) and estimation_id.startswith('pattern_matched_'):
                    estimation_19_id = int(estimation_id.replace('pattern_matched_', ''))
                    estimation_19 = record.env['fm.amc.estimation'].browse(estimation_19_id)
                    if estimation_19.exists():
                        sale_order_fields = record.env['sale.order']._fields
                        if 'is_estimation' in sale_order_fields:
                            quotation_vals['is_estimation'] = True
                            _logger.info("✅ Set is_estimation checkbox to True for quotation %s", quotation_number)
                        
                        if 'estimation_id' in sale_order_fields:
                            quotation_vals['estimation_id'] = estimation_19.id
                            _logger.info("✅ Set estimation_id to %s (%s) for quotation %s", 
                                       estimation_19.id, estimation_19.name, quotation_number)
                        
                        _logger.info("✅ Successfully linked estimation %s (ID: %s) to quotation %s via pattern matching", 
                                   estimation_19.name, estimation_19.id, quotation_number)
                else:
                    # Normal case: estimation_id from Odoo 14
                    estimation_id_val = estimation_id[0] if isinstance(estimation_id, list) else estimation_id
                    if estimation_id_val:
                        try:
                            # Try to get estimation from Odoo 14
                            estimation_data_14 = client.search_read(
                                'crm.estimation',
                                [('id', '=', estimation_id_val)],
                                ['name'],
                                limit=1
                            )
                            if not estimation_data_14:
                                # Try alternative model names
                                for model_name in ['fm.amc.estimation', 'estimation.estimation']:
                                    try:
                                        estimation_data_14 = client.search_read(
                                            model_name,
                                            [('id', '=', estimation_id_val)],
                                            ['name'],
                                            limit=1
                                        )
                                        if estimation_data_14:
                                            break
                                    except:
                                        continue
                            
                            if estimation_data_14:
                                estimation_number = estimation_data_14[0].get('name')
                                if estimation_number:
                                    # Find estimation in Odoo 19 by number
                                    estimation_19 = record.env['fm.amc.estimation'].search([
                                        ('name', '=', estimation_number)
                                    ], limit=1)
                                    
                                    if estimation_19:
                                        # Set estimation checkbox and estimation_id
                                        sale_order_fields = record.env['sale.order']._fields
                                        if 'is_estimation' in sale_order_fields:
                                            quotation_vals['is_estimation'] = True
                                            _logger.info("✅ Set is_estimation checkbox to True for quotation %s", quotation_number)
                                        
                                        if 'estimation_id' in sale_order_fields:
                                            quotation_vals['estimation_id'] = estimation_19.id
                                            _logger.info("✅ Set estimation_id to %s (%s) for quotation %s", 
                                                       estimation_19.id, estimation_number, quotation_number)
                                        
                                        _logger.info("✅ Successfully linked estimation %s (ID: %s) to quotation %s", 
                                                   estimation_number, estimation_19.id, quotation_number)
                                    else:
                                        _logger.warning("⚠️ Estimation %s not found in Odoo 19 for quotation %s", estimation_number, quotation_number)
                                else:
                                    _logger.warning("⚠️ Estimation number not found in Odoo 14 data for quotation %s", quotation_number)
                            else:
                                _logger.warning("⚠️ Estimation data not found in Odoo 14 for ID %s (quotation %s)", estimation_id_val, quotation_number)
                        except Exception as e:
                            _logger.warning("Could not link estimation to quotation %s: %s", quotation_number, str(e))
            
            _logger.info("💾 Creating quotation in Odoo 19...")
            quotation = record.env['sale.order'].create(quotation_vals)
            _logger.info("✅ Quotation created in Odoo 19: %s (ID: %s)", quotation.name, quotation.id)
            
            # Preserve original creation date
            src_create_date = quotation_data.get('create_date')
            if src_create_date:
                try:
                    record.env.cr.execute(
                        """
                        UPDATE sale_order
                           SET create_date = %s,
                               write_date = COALESCE(write_date, %s)
                         WHERE id = %s
                        """,
                        (src_create_date, src_create_date, quotation.id),
                    )
                except Exception as e:
                    _logger.warning("Could not set original create_date: %s", str(e))
            
            _logger.info("📝 Creating quotation lines...")
            wizard._create_quotation_lines(quotation, quotation_data, client)
            record.env.cr.commit()
            _logger.info("✅ Quotation lines created for %s", quotation_number)
            
            # Update status to migrated
            record.write({
                'status': 'migrated',
                'status_message': 'Successfully migrated',
                'odoo19_quotation_id': quotation.id,
                'in_system_quotation_number': quotation.name,
                'migration_date': fields.Datetime.now(),
                'error_message': False,
            })
            record.env.cr.commit()
            _logger.info("✅ Status updated to 'migrated' for %s", quotation_number)
            
            # Send success notification
            self._send_migration_notification(record, 'migrated', 'Successfully migrated', quotation.name)
            
            _logger.info("✅ Successfully migrated %s (%s/%s)", quotation_number, current_index + 1, len(record_ids))
            
        except Exception as e:
            error_msg = str(e)
            _logger.error("❌ Error migrating quotation %s: %s", quotation_number, error_msg, exc_info=True)
            
            # Ensure status is updated to error (in case migration hung)
            try:
                record.write({
                    'status': 'error',
                    'status_message': 'Migration failed',
                    'error_message': error_msg[:500] if len(error_msg) > 500 else error_msg,  # Limit error message length
                })
                record.env.flush_all()  # Flush instead of commit to avoid breaking savepoint
                _logger.info("✅ Status updated to 'error' for %s", quotation_number)
            except Exception as status_error:
                _logger.error("❌ Failed to update error status: %s", str(status_error))
            
            # Send error notification
            try:
                self._send_migration_notification(record, 'error', error_msg)
            except:
                pass  # Don't fail if notification fails
        
        # Automatically start next migration
        # IMPORTANT: Flush all changes before enqueueing next job (don't commit - let queue job runner handle it)
        record.env.flush_all()
        
        if current_index + 1 < len(record_ids):
            next_index = current_index + 1
            next_record_id = record_ids[next_index]
            _logger.info("🔄 Enqueueing next migration (%s/%s): record_id=%s", next_index + 1, len(record_ids), next_record_id)
            
            try:
                # Use a fresh recordset from the environment to ensure proper context
                # This is critical - we need a fresh env in queue job context
                fresh_env = record.env
                next_record = fresh_env['eq.migration.quotation'].browse(next_record_id)
                
                if not next_record.exists():
                    _logger.error("Next record %s does not exist, stopping sequential migration", next_record_id)
                    # Mark remaining as error
                    remaining_ids = record_ids[next_index:]
                    remaining_records = fresh_env['eq.migration.quotation'].browse(remaining_ids)
                    remaining_records.write({
                        'status': 'error',
                        'status_message': 'Record not found',
                        'error_message': 'Record %s does not exist' % next_record_id,
                    })
                    fresh_env.flush_all()  # Flush instead of commit to avoid breaking savepoint
                    return
                
                # DON'T update next record status here - it will be updated when the job actually starts
                # Just enqueue the next job - use with_delay() on the fresh recordset
                job = next_record.with_delay()._migrate_sequential(record_ids, next_index)
                _logger.info("✅ Next job enqueued: job_uuid=%s, record_id=%s", getattr(job, 'uuid', 'N/A'), next_record_id)
                
                # Small delay to let job be created in database
                import time
                time.sleep(0.3)
                
                # Verify the job was created
                pending_jobs = fresh_env['queue.job'].search_count([
                    ('state', '=', 'pending'),
                ])
                migration_jobs = fresh_env['queue.job'].search_count([
                    ('state', '=', 'pending'),
                    ('model_name', '=', 'eq.migration.quotation'),
                    ('method_name', '=', '_migrate_sequential'),
                ])
                _logger.info("📊 Queue status: %s total pending jobs, %s migration jobs", pending_jobs, migration_jobs)
                
                if migration_jobs == 0:
                    _logger.warning("⚠️ No migration jobs found in queue after enqueueing! This might indicate a problem.")
                
            except Exception as e:
                _logger.error("❌ Failed to enqueue next migration job: %s", str(e), exc_info=True)
                # Mark remaining records as error
                try:
                    remaining_ids = record_ids[next_index:]
                    remaining_records = record.env['eq.migration.quotation'].browse(remaining_ids)
                    remaining_records.write({
                        'status': 'error',
                        'status_message': 'Failed to queue next job: %s' % str(e),
                        'error_message': 'Sequential migration stopped: %s' % str(e),
                    })
                    record.env.flush_all()  # Flush instead of commit to avoid breaking savepoint
                except:
                    pass
        else:
            _logger.info("✅ All migrations completed!")
    
    def _send_migration_notification(self, record, status, message, quotation_name=None):
        """
        Send notification to user about migration status.
        Creates a notification that will be shown in the UI via mail.message.
        """
        try:
            user = self.env.user
            
            # Determine notification type and title
            if status == 'migrated':
                title = '✅ Migration Complete'
                body = 'Quotation <strong>%s</strong> has been successfully migrated%s' % (
                    record.uploaded_quotation_number,
                    ' as <strong>%s</strong>' % quotation_name if quotation_name else ''
                )
            elif status == 'error':
                title = '❌ Migration Failed'
                body = 'Migration failed for quotation <strong>%s</strong>: %s' % (record.uploaded_quotation_number, message)
            else:
                title = 'ℹ️ Migration Update'
                body = 'Quotation <strong>%s</strong>: %s' % (record.uploaded_quotation_number, message)
            
            # Log for debugging
            _logger.info("📢 Notification: %s - %s", record.uploaded_quotation_number, message)
            
            # Create a mail.message notification (this appears in the user's notification center)
            try:
                # Use mail.thread to post a message
                if hasattr(record, 'message_post'):
                    record.with_context(mail_create_nolog=True).message_post(
                        body=body,
                        subject=title,
                        message_type='notification',
                        subtype_xmlid='mail.mt_note',
                    )
            except Exception as e:
                _logger.warning("Could not create mail notification: %s", str(e))
            
            # Also try bus notification for real-time updates
            try:
                from odoo.addons.bus.models.bus import bus_sendone
                bus_sendone(
                    self.env,
                    (self.env.cr.dbname, 'migration_notification', user.id),
                    {
                        'type': 'success' if status == 'migrated' else 'danger' if status == 'error' else 'info',
                        'title': title,
                        'message': body.replace('<strong>', '').replace('</strong>', ''),
                        'quotation': record.uploaded_quotation_number,
                        'record_id': record.id,
                        'sticky': False,
                    }
                )
            except (ImportError, Exception) as e:
                # Bus not available or error, skip - mail.message will handle it
                _logger.debug("Bus notification skipped: %s", str(e))
            
        except Exception as e:
            _logger.error("Error sending notification: %s", str(e))
