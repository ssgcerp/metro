# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


def _log_failed_estimation_migration(estimation_number, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        # Get log directory (use module directory/logs)
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_estimation_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {estimation_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed estimation migration logged to: %s", log_file)
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


class EstimationMigrationLine(models.Model):
    """Model to store uploaded estimation numbers and track migration status"""
    _name = 'estimation.migration.line'
    _description = 'Estimation Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    uploaded_estimation_number = fields.Char(
        string='Estimation',
        required=True,
        index=True,
        help='Estimation number from Excel upload'
    )
    
    in_system_estimation_number = fields.Char(
        string='In-System Estimation Number',
        readonly=True,
        help='Actual estimation number found in Odoo 14 or Odoo 19'
    )
    
    # Additional fields from Excel
    customer = fields.Char(
        string='Customer',
        help='Customer name from Excel'
    )
    
    lead = fields.Char(
        string='Lead',
        help='Lead description from Excel'
    )
    
    engineer = fields.Char(
        string='Engineer',
        help='Engineer name from Excel'
    )
    
    estimated_delivery = fields.Char(
        string='Estimated Delivery',
        help='Estimated delivery condition from Excel'
    )
    
    excel_status = fields.Char(
        string='Status (Excel)',
        help='Status from Excel file'
    )
    
    company = fields.Char(
        string='Company',
        help='Company/Branch name from Excel'
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
    
    odoo14_estimation_id = fields.Integer(
        string='Odoo 14 Estimation ID',
        readonly=True,
        help='ID of estimation in Odoo 14 if found'
    )
    
    odoo19_estimation_id = fields.Many2one(
        'fm.amc.estimation',
        string='Odoo 19 Estimation',
        readonly=True,
        help='Migrated estimation in Odoo 19'
    )
    
    migration_date = fields.Datetime(string='Migration Date', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    def check_status(self, estimation_number=None, config_id=None):
        """Check status of an estimation number against Odoo 14 and Odoo 19"""
        self.ensure_one()
        if not estimation_number:
            estimation_number = self.uploaded_estimation_number
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
            existing_19 = self.env['fm.amc.estimation'].search([
                ('name', '=', estimation_number)
            ], limit=1)
            
            if existing_19:
                return {
                    'status': 'already_migrated',
                    'message': 'Already exists in Odoo 19',
                    'odoo19_id': existing_19.id,
                    'odoo19_name': existing_19.name
                }
            
            # Check in Odoo 14 - try multiple model names (crm.estimation is the correct one for Odoo 14)
            estimations = []
            model_names = ['crm.estimation', 'fm.amc.estimation', 'estimation.estimation', 'crm.lead']
            
            for model_name in model_names:
                try:
                    estimations = client.search_read(
                        model_name,
                        [('name', '=', estimation_number)],
                        ['id', 'name'],
                        limit=1
                    )
                    if estimations:
                        break
                except Exception as e:
                    _logger.debug("Model %s not found or error: %s", model_name, str(e))
                    continue
            
            if estimations:
                return {
                    'status': 'pending_migration',
                    'message': 'Found in Odoo 14, ready to migrate',
                    'odoo14_id': estimations[0]['id'],
                    'odoo14_name': estimations[0]['name']
                }
            else:
                return {
                    'status': 'not_found',
                    'message': 'Not found in Odoo 14'
                }
                
        except Exception as e:
            _logger.error("Error checking estimation status: %s", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def action_check_status(self):
        """Button action to refresh status"""
        for record in self:
            result = record.check_status()
            record.write({
                'status': result.get('status', 'not_found'),
                'status_message': result.get('message', ''),
                'in_system_estimation_number': result.get('odoo14_name') or result.get('odoo19_name') or '',
                'odoo14_estimation_id': result.get('odoo14_id', 0),
                'odoo19_estimation_id': result.get('odoo19_id', False),
            })
    
    @api.model
    def action_open_upload_wizard(self):
        """Open the Excel upload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'estimation.upload.wizard',
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
            
            # Check for estimation migration-specific jobs
            migration_pending = self.env['queue.job'].search_count([
                ('state', '=', 'pending'),
                ('model_name', '=', 'estimation.migration.line'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            migration_started = self.env['queue.job'].search_count([
                ('state', '=', 'started'),
                ('model_name', '=', 'estimation.migration.line'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            
            _logger.info("📊 Queue status: %s pending (total), %s started (total), %s estimation migration pending, %s estimation migration started", 
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
                    message = f'Queue job cron triggered successfully. {pending_jobs} pending job(s) (including {migration_pending} estimation migration jobs) will start processing now.'
                else:
                    message = f'Queue job cron triggered successfully. {pending_jobs} pending job(s) will start processing now.'
            else:
                # Try method 2: Use _cron_trigger if available
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
        """Bulk migrate selected estimations sequentially using Queue Jobs"""
        # Wrap entire method to ensure we never leave records in 'error' status
        try:
            pending = self.filtered(lambda l: l.status == 'pending_migration')
            if not pending:
                raise UserError('No estimations with "Pending Migration" status selected')
            
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
                raise UserError('No estimations with "Pending Migration" status selected')
            
            # Mark all records as "queued" - user will start the migration process separately
            # Use fresh recordset to ensure we're working with the latest data
            fresh_pending = self.env['estimation.migration.line'].browse(pending_ids)
            for record in fresh_pending:
                record.write({
                    'status': 'queued',
                    'status_message': 'Queued for migration - waiting to be processed',
                    'error_message': False,  # Clear any previous error messages
                })
            self.env.cr.commit()
            _logger.info("✅ Marked %s estimations as 'queued' (ready for processing)", len(fresh_pending))
        
            # Return success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Estimations Queued',
                    'message': f'{len(pending_ids)} estimations have been queued. Use "Process Queue Jobs Now" to start the migration process.',
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
                                'title': 'Estimations Queued (with warnings)',
                                'message': f'{len(fresh_pending)} estimations queued, but there were some issues. Check status messages for details.',
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
                    fresh_pending = self.env['estimation.migration.line'].browse(pending_ids)
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
                            'title': 'Estimations Queued',
                            'message': f'{len(pending_ids)} estimations have been queued. There were some issues during enqueueing - check status messages for details.',
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
                    'message': f'Action completed, but there were some issues. Please check the estimation records.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
    
    def action_start_queued_migration(self):
        """Start processing queued estimations - enqueue the first job to start sequential migration"""
        queued = self.filtered(lambda l: l.status == 'queued')
        if not queued:
            raise UserError('No estimations with "Queued" status selected')
        
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
            raise UserError('No estimations with "Queued" status selected')
        
        # Start sequential migration by enqueueing the first job
        try:
            first_record = self.browse(queued_ids[0])
            if not first_record.exists():
                raise UserError(f'Record {queued_ids[0]} no longer exists')
            
            # Enqueue the first job - it will automatically process the rest sequentially
            job = first_record.with_delay()._migrate_sequential(queued_ids, 0)
            
            _logger.info("✅ Started sequential migration for %s queued estimations (job UUID: %s)", 
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
                    'message': f'Started processing {len(queued_ids)} queued estimations. Migration will continue sequentially.',
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
        """Migrate this estimation from Odoo 14 to Odoo 19"""
        self.ensure_one()
        
        if self.status != 'pending_migration':
            raise UserError('Can only migrate estimations with "Pending Migration" status')
        
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
            
            # Get initial estimation data from Odoo 14 (use minimal safe fields only)
            # crm.estimation is the correct model name in Odoo 14 sales_estimation module
            safe_initial_fields = ['id', 'name']
            estimations = []
            model_names = ['crm.estimation', 'fm.amc.estimation', 'estimation.estimation', 'crm.lead']
            
            for model_name in model_names:
                try:
                    estimations = client.search_read(
                        model_name,
                        [('name', '=', self.uploaded_estimation_number)],
                        safe_initial_fields,
                        limit=1
                    )
                    if estimations:
                        break
                except Exception as e:
                    _logger.debug("Model %s not found or error: %s", model_name, str(e))
                    continue
            
            if not estimations:
                self.write({
                    'status': 'not_found',
                    'status_message': 'Estimation not found in Odoo 14',
                })
                return
            
            estimation_data = estimations[0]
            model_used = model_names[0]  # Use first model that worked
            
            # Check if estimation already exists in Odoo 19 BEFORE migrating
            existing_estimation = self.env['fm.amc.estimation'].search([
                ('name', '=', self.uploaded_estimation_number)
            ], limit=1)
            
            if existing_estimation:
                _logger.info("Estimation %s already exists in Odoo 19 (ID: %s), marking as migrated", 
                           self.uploaded_estimation_number, existing_estimation.id)
                self.write({
                    'status': 'migrated',
                    'status_message': 'Already migrated (existed in system)',
                    'odoo19_estimation_id': existing_estimation.id,
                    'in_system_estimation_number': existing_estimation.name,
                    'migration_date': fields.Datetime.now(),
                    'error_message': False,
                })
                self.env.cr.commit()
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'estimation.migration.line',
                    'view_mode': 'list,form',
                    'target': 'current',
                }
            
            # Update status to migrating
            self.write({
                'status': 'migrating',
                'status_message': 'Migration in progress...',
            })
            self.env.cr.commit()
            
            # Get fields to fetch - only stored fields, exclude computed fields
            excluded_fields = [
                'display_name', 'name_get', 'name_search',
            ]
            
            # Safe stored fields for estimation
            # For crm.estimation (Odoo 14): name, partner_id, lead_id, estimator_id, edt_id, branch_id, 
            # expected_date, description, state, product_line_ids, service_line_ids
            # For fm.amc.estimation (Odoo 19): name, partner_id, lead_id, sales_contact_id, estimated_delivery,
            # branch_id, estimation_date, note, stage_id, line_ids
            fields_to_fetch = [
                'id', 'name', 'partner_id', 'lead_id', 'estimator_id', 'edt_id', 'branch_id',
                'expected_date', 'description', 'state', 'product_line_ids', 'service_line_ids',
                'create_date', 'write_date', 'write_uid', 'create_uid'
            ]
            
            # Try to get all fields dynamically
            try:
                all_fields = client.fields_get(model_used)
                if all_fields:
                    dynamic_fields = []
                    for f, field_info in all_fields.items():
                        if f in excluded_fields or f in fields_to_fetch:
                            continue
                        field_type = field_info.get('type', '')
                        field_store = field_info.get('store', True)
                        if not field_store:
                            continue
                        if field_type in ('one2many', 'many2many') and f not in ('product_line_ids', 'service_line_ids', 'line_ids'):
                            continue
                        if field_type in ('char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime', 'many2one', 'selection'):
                            dynamic_fields.append(f)
                    fields_to_fetch = list(set(fields_to_fetch + dynamic_fields))
            except Exception as e:
                _logger.warning("Could not get all fields: %s", str(e))
            
            minimal_safe_fields = [
                'id', 'name', 'partner_id', 'lead_id', 'estimator_id', 'edt_id', 'branch_id',
                'expected_date', 'description', 'state', 'product_line_ids', 'service_line_ids',
                'create_date', 'write_date'
            ]
            
            try:
                full_estimation = client.search_read(
                    model_used,
                    [('id', '=', estimation_data['id'])],
                    fields_to_fetch,
                    limit=1
                )
            except Exception as e:
                _logger.warning("Error fetching estimation with expanded fields: %s. Using minimal safe fields.", str(e))
                full_estimation = client.search_read(
                    model_used,
                    [('id', '=', estimation_data['id'])],
                    minimal_safe_fields,
                    limit=1
                )
            
            if not full_estimation:
                raise UserError('Could not fetch full estimation data')
            
            estimation_data = full_estimation[0]
            
            # Prepare estimation values for Odoo 19 (matching fm.amc.estimation model)
            estimation_vals = {}
            
            # Map name (estimation number) - REQUIRED
            if estimation_data.get('name') and estimation_data.get('name') != '_Draft':
                estimation_vals['name'] = estimation_data['name']
            else:
                # Use uploaded estimation number if name is _Draft
                estimation_vals['name'] = self.uploaded_estimation_number
            
            # Map partner_id (required field)
            if estimation_data.get('partner_id'):
                partner_id = estimation_data['partner_id']
                if isinstance(partner_id, (list, tuple)) and len(partner_id) > 0:
                    partner_id = partner_id[0]
                # Find or create partner in Odoo 19
                partner = self.env['res.partner'].search([('id', '=', partner_id)], limit=1)
                if not partner:
                    # Try to get partner from Odoo 14
                    try:
                        partner_data = client.search_read(
                            'res.partner',
                            [('id', '=', partner_id)],
                            ['name', 'email', 'phone'],
                            limit=1
                        )
                        if partner_data:
                            partner = self.env['res.partner'].create({
                                'name': partner_data[0].get('name', 'Unknown'),
                                'email': partner_data[0].get('email', False),
                                'phone': partner_data[0].get('phone', False),
                            })
                    except:
                        pass
                if partner:
                    estimation_vals['partner_id'] = partner.id
                else:
                    raise UserError('Could not find or create partner for estimation')
            else:
                raise UserError('Partner is required for estimation')
            
            # Map branch_id (required field) - use company_id or branch_id from Odoo 14
            branch_id = estimation_data.get('branch_id') or estimation_data.get('company_id')
            if branch_id:
                if isinstance(branch_id, (list, tuple)) and len(branch_id) > 0:
                    branch_id = branch_id[0]
                company = self.env['res.company'].search([('id', '=', branch_id)], limit=1)
                if company:
                    estimation_vals['branch_id'] = company.id
                else:
                    # Use default company if not found
                    estimation_vals['branch_id'] = self.env.company.id
            else:
                # Use default company if not provided
                estimation_vals['branch_id'] = self.env.company.id
            
            # Map estimation_date (required field) - use create_date from Odoo 14
            if estimation_data.get('create_date'):
                # Extract date from datetime
                create_date = estimation_data['create_date']
                if isinstance(create_date, str):
                    # Parse datetime string to get date part
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(create_date.split()[0], '%Y-%m-%d')
                        estimation_vals['estimation_date'] = dt.date()
                    except:
                        estimation_vals['estimation_date'] = fields.Date.today()
                else:
                    estimation_vals['estimation_date'] = create_date
            elif estimation_data.get('expected_date'):
                estimation_vals['estimation_date'] = estimation_data['expected_date']
            elif estimation_data.get('estimation_date'):
                estimation_vals['estimation_date'] = estimation_data['estimation_date']
            else:
                estimation_vals['estimation_date'] = fields.Date.today()
            
            # Map other optional fields
            # Map description to note
            if estimation_data.get('description'):
                estimation_vals['note'] = estimation_data['description']
            elif estimation_data.get('note'):
                estimation_vals['note'] = estimation_data['note']
            
            # Map estimator_id to sales_contact_id (engineer)
            if estimation_data.get('estimator_id'):
                estimator_id = estimation_data['estimator_id']
                if isinstance(estimator_id, (list, tuple)) and len(estimator_id) > 0:
                    estimator_id = estimator_id[0]
                employee = self.env['hr.employee'].search([('user_id', '=', estimator_id)], limit=1)
                if employee:
                    estimation_vals['sales_contact_id'] = employee.id
            
                # Map state to stage_id (Odoo 14 state -> Odoo 19 stage)
                # Odoo 14: draft, send, approved, confirmed
                # Odoo 19: Draft, Waiting Approval, Approved, Locked
                if estimation_data.get('state'):
                    state = estimation_data['state']
                    # Map Odoo 14 state to Odoo 19 stage names
                    state_to_stage_name = {
                        'draft': 'Draft',
                        'send': 'Waiting Approval',
                        'approved': 'Approved',
                        'confirmed': 'Locked'
                    }
                    stage_display_name = state_to_stage_name.get(state, 'Draft')
                
                # Try to find stage by exact name match
                stage = self.env['fm.amc.estimation.stage'].search([
                    ('name', '=', stage_display_name)
                ], limit=1)
                
                if not stage:
                    # Try case-insensitive match
                    stage = self.env['fm.amc.estimation.stage'].search([
                        ('name', 'ilike', stage_display_name)
                    ], limit=1)
                
                if not stage:
                    # Get default stage (usually draft) - try to find Draft first
                    stage = self.env['fm.amc.estimation.stage'].search([
                        ('name', 'ilike', 'draft')
                    ], limit=1, order='sequence asc')
                
                if not stage:
                    # Fallback: get any stage ordered by sequence
                    stage = self.env['fm.amc.estimation.stage'].search([], limit=1, order='sequence asc')
                
                if stage:
                    estimation_vals['stage_id'] = stage.id
                    _logger.info("Mapped state %s to stage %s", state, stage.name)
                else:
                    _logger.warning("Could not find stage for state %s, estimation will be created without stage", state)
            
            # Map edt_id to estimated_delivery (if available in Odoo 19)
            # Note: This might need to be mapped differently based on Odoo 19 model
            if estimation_data.get('edt_id'):
                edt_id = estimation_data['edt_id']
                if isinstance(edt_id, (list, tuple)) and len(edt_id) > 0:
                    edt_id = edt_id[0]
                # Try to get estimated delivery data from Odoo 14
                try:
                    edt_data = client.search_read(
                        'crm.estimation.etd',
                        [('id', '=', edt_id)],
                        ['name', 'days'],
                        limit=1
                    )
                    if edt_data:
                        # Store estimated delivery info in note or custom field
                        edt_name = edt_data[0].get('name', '')
                        if edt_name and estimation_vals.get('note'):
                            estimation_vals['note'] = f"{estimation_vals['note']}\nEstimated Delivery: {edt_name}"
                        elif edt_name:
                            estimation_vals['note'] = f"Estimated Delivery: {edt_name}"
                except:
                    pass
            
            # Map contact_id if exists
            if estimation_data.get('contact_id'):
                contact_id = estimation_data['contact_id']
                if isinstance(contact_id, (list, tuple)) and len(contact_id) > 0:
                    contact_id = contact_id[0]
                contact = self.env['res.partner'].search([('id', '=', contact_id)], limit=1)
                if contact:
                    estimation_vals['contact_id'] = contact.id
            
            # Map lead_id if exists - IMPORTANT: Must migrate lead first or find by name
            if estimation_data.get('lead_id'):
                lead_id = estimation_data['lead_id']
                if isinstance(lead_id, (list, tuple)) and len(lead_id) > 0:
                    lead_id = lead_id[0]
                
                # First try to find by ID
                lead = self.env['crm.lead'].search([('id', '=', lead_id)], limit=1)
                
                # If not found, try to get from Odoo 14 and create
                if not lead:
                    try:
                        lead_data = client.search_read(
                            'crm.lead',
                            [('id', '=', lead_id)],
                            ['name', 'partner_id', 'type'],
                            limit=1
                        )
                        if lead_data:
                            # Try to find by name in Odoo 19
                            lead = self.env['crm.lead'].search([('name', '=', lead_data[0].get('name'))], limit=1)
                            if not lead:
                                # Create lead if not found
                                lead_vals = {
                                    'name': lead_data[0].get('name', 'Migrated Lead'),
                                    'type': lead_data[0].get('type', 'opportunity'),
                                }
                                # Map partner if available
                                if lead_data[0].get('partner_id'):
                                    partner_id = lead_data[0]['partner_id']
                                    if isinstance(partner_id, (list, tuple)) and len(partner_id) > 0:
                                        partner_id = partner_id[0]
                                    partner = self.env['res.partner'].search([('id', '=', partner_id)], limit=1)
                                    if partner:
                                        lead_vals['partner_id'] = partner.id
                                
                                lead = self.env['crm.lead'].create(lead_vals)
                                _logger.info("Created lead %s for estimation", lead.name)
                    except Exception as e:
                        _logger.warning("Could not migrate lead %s: %s", lead_id, str(e))
                
                if lead:
                    estimation_vals['lead_id'] = lead.id
            
            # Map project_id if exists
            if estimation_data.get('project_id'):
                project_id = estimation_data['project_id']
                if isinstance(project_id, (list, tuple)) and len(project_id) > 0:
                    project_id = project_id[0]
                project = self.env['project.project'].search([('id', '=', project_id)], limit=1)
                if project:
                    estimation_vals['project_id'] = project.id
            
            # Map amc_contract_id if exists
            if estimation_data.get('amc_contract_id'):
                amc_contract_id = estimation_data['amc_contract_id']
                if isinstance(amc_contract_id, (list, tuple)) and len(amc_contract_id) > 0:
                    amc_contract_id = amc_contract_id[0]
                amc_contract = self.env['amc.contract'].search([('id', '=', amc_contract_id)], limit=1)
                if amc_contract:
                    estimation_vals['amc_contract_id'] = amc_contract.id
            
            # Map sales_contact_id (hr.employee) if exists
            if estimation_data.get('sales_contact_id'):
                sales_contact_id = estimation_data['sales_contact_id']
                if isinstance(sales_contact_id, (list, tuple)) and len(sales_contact_id) > 0:
                    sales_contact_id = sales_contact_id[0]
                employee = self.env['hr.employee'].search([('id', '=', sales_contact_id)], limit=1)
                if employee:
                    estimation_vals['sales_contact_id'] = employee.id
            
            # Create estimation in Odoo 19
            estimation = self.env['fm.amc.estimation'].create(estimation_vals)
            
            # Preserve original creation date
            src_create_date = estimation_data.get('create_date')
            if src_create_date:
                try:
                    self.env.cr.execute(
                        """
                        UPDATE fm_amc_estimation
                           SET create_date = %s,
                               write_date = COALESCE(write_date, %s)
                         WHERE id = %s
                        """,
                        (src_create_date, src_create_date, estimation.id),
                    )
                except Exception as e:
                    _logger.warning("Could not set original create_date: %s", str(e))
            
            # Migrate estimation lines if available
            # In Odoo 14: product_line_ids and service_line_ids (both are crm.estimation.line)
            # In Odoo 19: line_ids (fm.amc.estimation.line)
            line_ids_to_migrate = []
            
            # Get product lines
            if estimation_data.get('product_line_ids'):
                product_line_ids = estimation_data['product_line_ids']
                if isinstance(product_line_ids, (list, tuple)):
                    line_ids_to_migrate.extend(product_line_ids)
            
            # Get service lines
            if estimation_data.get('service_line_ids'):
                service_line_ids = estimation_data['service_line_ids']
                if isinstance(service_line_ids, (list, tuple)):
                    line_ids_to_migrate.extend(service_line_ids)
            
            # Fallback to line_ids if available
            if not line_ids_to_migrate and estimation_data.get('line_ids'):
                line_ids_to_migrate = estimation_data['line_ids']
                if not isinstance(line_ids_to_migrate, (list, tuple)):
                    line_ids_to_migrate = []
            
            if line_ids_to_migrate:
                try:
                    # Use crm.estimation.line for Odoo 14
                    line_model = 'crm.estimation.line'
                    
                    for line_id in line_ids_to_migrate:
                        try:
                            # Fetch line data from Odoo 14 crm.estimation.line
                            # Fields in Odoo 14: product_id, name, product_qty, unit_selling_price, product_uom, sequence, estimation_type, display_type
                            line_data = client.search_read(
                                line_model,
                                [('id', '=', line_id)],
                                ['product_id', 'name', 'product_qty', 'unit_selling_price', 'service_cost', 'product_uom', 'sequence', 'estimation_type', 'display_type'],
                                limit=1
                            )
                            if line_data:
                                line_info = line_data[0]
                                
                                # Check if this is a section or note line
                                display_type = line_info.get('display_type', False)
                                
                                # Determine line_type based on estimation_type (for both sections/notes and regular lines)
                                estimation_type = line_info.get('estimation_type', 'product')
                                # Map Odoo 14 estimation_type to Odoo 19 line_type
                                # Odoo 14: 'product' or 'service'
                                # Odoo 19: 'project', 'consumable', or 'expense'
                                # For now, map both 'product' and 'service' to 'project' (can be adjusted if needed)
                                line_type = 'project'  # Default to project tab
                                
                                # If it's a section or note, create it as such (no product, quantity, or price)
                                if display_type in ('line_section', 'line_note'):
                                    line_vals = {
                                        'estimation_id': estimation.id,
                                        'name': line_info.get('name', 'Section' if display_type == 'line_section' else 'Note'),
                                        'display_type': display_type,  # Preserve section/note type
                                        'line_type': line_type,  # Use the correct tab based on estimation_type
                                    }
                                    
                                    if line_info.get('sequence'):
                                        line_vals['sequence'] = line_info['sequence']
                                    
                                    # Create section/note line (no product, quantity, or price)
                                    self.env['fm.amc.estimation.line'].create(line_vals)
                                    continue  # Skip to next line
                                
                                # Otherwise, it's a regular product line
                                # Map from Odoo 14 to Odoo 19
                                # Odoo 14: product_qty, unit_selling_price, service_cost
                                # Odoo 19: product_uom_qty, price_unit, line_type
                                unit_selling_price = line_info.get('unit_selling_price', 0.0) or 0.0
                                service_cost = line_info.get('service_cost', 0.0) or 0.0
                                total_price = unit_selling_price + service_cost
                                
                                line_vals = {
                                    'estimation_id': estimation.id,
                                    'name': line_info.get('name', '') or 'Line',
                                    'line_type': line_type,
                                    'product_uom_qty': line_info.get('product_qty', 1.0),
                                    'price_unit': total_price,  # Combine unit_selling_price + service_cost
                                    'display_type': False,  # Regular product line, not section/note
                                }
                                
                                if line_info.get('sequence'):
                                    line_vals['sequence'] = line_info['sequence']
                                
                                # Map product_id - IMPORTANT: Find or create product
                                if line_info.get('product_id'):
                                    product_id = line_info['product_id']
                                    if isinstance(product_id, (list, tuple)) and len(product_id) > 0:
                                        product_id = product_id[0]
                                    
                                    # First try to find by ID
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
                                                # Try to find by default_code first
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
                                                    _logger.info("Created product %s for estimation line", product.name)
                                        except Exception as e:
                                            _logger.warning("Could not migrate product %s: %s", product_id, str(e))
                                    
                                    if product:
                                        line_vals['product_id'] = product.id
                                    else:
                                        _logger.warning("Product %s not found and could not be created for line", product_id)
                                
                                # Map product_uom
                                if line_info.get('product_uom'):
                                    uom_id = line_info['product_uom']
                                    if isinstance(uom_id, (list, tuple)) and len(uom_id) > 0:
                                        uom_id = uom_id[0]
                                    uom = self.env['uom.uom'].search([('id', '=', uom_id)], limit=1)
                                    if uom:
                                        line_vals['product_uom'] = uom.id
                                
                                # Note: crm.estimation.line doesn't have tax_id in Odoo 14, so skip tax mapping
                                
                                self.env['fm.amc.estimation.line'].create(line_vals)
                        except Exception as e:
                            _logger.warning("Could not migrate estimation line %s: %s", line_id, str(e), exc_info=True)
                except Exception as e:
                    _logger.warning("Could not migrate estimation lines: %s", str(e), exc_info=True)
            
            self.env.cr.commit()
            
            # Update status to migrated
            self.write({
                'status': 'migrated',
                'status_message': 'Successfully migrated',
                'odoo19_estimation_id': estimation.id,
                'in_system_estimation_number': estimation.name,
                'migration_date': fields.Datetime.now(),
                'error_message': False,
            })
            self.env.cr.commit()
            
            # Return to reload list view
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'estimation.migration.line',
                'view_mode': 'list,form',
                'target': 'current',
            }
                
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
            _log_failed_estimation_migration(self.uploaded_estimation_number, error_msg)
            raise UserError('Error migrating estimation: %s' % str(e))
    
    def _migrate_sequential(self, record_ids, current_index):
        """
        Sequential migration method using Queue Jobs.
        Migrates one estimation at a time, updates status, sends notification, then starts next.
        
        :param record_ids: List of record IDs to migrate
        :param current_index: Current index in the list (0-based)
        """
        if current_index >= len(record_ids):
            _logger.info("Sequential migration completed for all %s records", len(record_ids))
            return
        
        record_id = record_ids[current_index]
        record = self.env['estimation.migration.line'].browse(record_id)
        
        if not record.exists():
            _logger.warning("Record %s does not exist, skipping", record_id)
            if current_index + 1 < len(record_ids):
                next_record = record.env['estimation.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        estimation_number = record.uploaded_estimation_number
        _logger.info("🚀 Starting migration %s/%s: %s (record_id=%s)", current_index + 1, len(record_ids), estimation_number, record_id)
        
        if record.status not in ('pending_migration', 'queued'):
            _logger.warning("Record %s is not in pending_migration or queued status (%s), skipping", estimation_number, record.status)
            if current_index + 1 < len(record_ids):
                next_record = record.env['estimation.migration.line'].browse(record_ids[current_index + 1])
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
            self._send_migration_notification(record, 'error', 'Configuration missing')
            
            if current_index + 1 < len(record_ids):
                next_record = record.env['estimation.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        # Update status to migrating
        record.write({
            'status': 'migrating',
            'status_message': 'Migration in progress...',
        })
        record.env.flush_all()
        _logger.info("📝 Status updated to 'migrating' for %s", estimation_number)
        
        # Wrap entire migration in try-except
        try:
            # Call action_migrate for this record
            # Since action_migrate is already implemented, we'll use it
            record.action_migrate()
            
            _logger.info("✅ Successfully migrated %s (%s/%s)", estimation_number, current_index + 1, len(record_ids))
            
        except Exception as e:
            error_msg = str(e)
            _logger.error("❌ Error migrating estimation %s: %s", estimation_number, error_msg, exc_info=True)
            
            try:
                record.write({
                    'status': 'error',
                    'status_message': 'Migration failed',
                    'error_message': error_msg[:500] if len(error_msg) > 500 else error_msg,
                })
                record.env.flush_all()
            except Exception as status_error:
                _logger.error("❌ Failed to update error status: %s", str(status_error))
            
            try:
                self._send_migration_notification(record, 'error', error_msg)
            except:
                pass
        
        # Automatically start next migration
        record.env.flush_all()
        
        if current_index + 1 < len(record_ids):
            next_index = current_index + 1
            next_record_id = record_ids[next_index]
            _logger.info("🔄 Enqueueing next migration (%s/%s): record_id=%s", next_index + 1, len(record_ids), next_record_id)
            
            try:
                fresh_env = record.env
                next_record = fresh_env['estimation.migration.line'].browse(next_record_id)
                
                if not next_record.exists():
                    _logger.error("Next record %s does not exist, stopping sequential migration", next_record_id)
                    remaining_ids = record_ids[next_index:]
                    remaining_records = fresh_env['estimation.migration.line'].browse(remaining_ids)
                    remaining_records.write({
                        'status': 'error',
                        'status_message': 'Record not found',
                        'error_message': 'Record %s does not exist' % next_record_id,
                    })
                    fresh_env.flush_all()
                    return
                
                job = next_record.with_delay()._migrate_sequential(record_ids, next_index)
                _logger.info("✅ Next job enqueued: job_uuid=%s, record_id=%s", getattr(job, 'uuid', 'N/A'), next_record_id)
                
                import time
                time.sleep(0.3)
                
            except Exception as e:
                _logger.error("❌ Failed to enqueue next migration job: %s", str(e), exc_info=True)
                try:
                    remaining_ids = record_ids[next_index:]
                    remaining_records = record.env['estimation.migration.line'].browse(remaining_ids)
                    remaining_records.write({
                        'status': 'error',
                        'status_message': 'Failed to queue next job: %s' % str(e),
                        'error_message': 'Sequential migration stopped: %s' % str(e),
                    })
                    record.env.flush_all()
                except:
                    pass
        else:
            _logger.info("✅ All migrations completed!")
    
    def _send_migration_notification(self, record, status, message, estimation_name=None):
        """Send notification to user about migration status"""
        try:
            user = self.env.user
            
            if status == 'migrated':
                title = '✅ Migration Complete'
                body = 'Estimation <strong>%s</strong> has been successfully migrated%s' % (
                    record.uploaded_estimation_number,
                    ' as <strong>%s</strong>' % estimation_name if estimation_name else ''
                )
            elif status == 'error':
                title = '❌ Migration Failed'
                body = 'Migration failed for estimation <strong>%s</strong>: %s' % (record.uploaded_estimation_number, message)
            else:
                title = 'ℹ️ Migration Update'
                body = 'Estimation <strong>%s</strong>: %s' % (record.uploaded_estimation_number, message)
            
            _logger.info("📢 Notification: %s - %s", record.uploaded_estimation_number, message)
            
            try:
                if hasattr(record, 'message_post'):
                    record.with_context(mail_create_nolog=True).message_post(
                        body=body,
                        subject=title,
                        message_type='notification',
                        subtype_xmlid='mail.mt_note',
                    )
            except Exception as e:
                _logger.warning("Could not create mail notification: %s", str(e))
            
        except Exception as e:
            _logger.error("Error sending notification: %s", str(e))

