# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


def _log_failed_migration(contract_number, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        # Get log directory (use module directory/logs)
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_amc_contract_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {contract_number} | {error_detail[:200]}\n")
        
        _logger.info("Failed AMC contract migration logged to: %s", log_file)
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


class AMCContractMigrationLine(models.Model):
    """Model to store uploaded AMC contract data from Excel and track migration status"""
    _name = 'amc.contract.migration.line'
    _description = 'AMC Contract Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # Excel Data Fields
    contract_number = fields.Char(
        string='Contract Number',
        required=True,
        index=True,
        help='Contract number from Excel (e.g., MFS/AMC/FUJ/1319/2025)'
    )
    
    start_date = fields.Date(
        string='Start Date',
        help='Start date from Excel'
    )
    
    end_date = fields.Date(
        string='End Date',
        help='End date from Excel'
    )
    
    customer_name = fields.Char(
        string='Customer Name',
        help='Customer name from Excel'
    )
    
    contract_value = fields.Float(
        string='Contract Value',
        help='Contract value from Excel'
    )
    
    status_name = fields.Char(
        string='Status (Excel)',
        help='Status from Excel (e.g., Confirmed)'
    )
    
    contract_date = fields.Date(
        string='Contract Date',
        help='Contract date from Excel'
    )
    
    odoo14_branch_id = fields.Integer(
        string='Odoo 14 Branch ID',
        help='Branch ID from Excel (used to map to Odoo 19 company)'
    )
    
    # Migration Fields
    status = fields.Selection([
        ('pending_migration', 'Pending Migration'),
        ('queued', 'Queued'),
        ('migrating', 'Migrating'),
        ('migrated', 'Migrated'),
        ('error', 'Error'),
    ], string='Migration Status', default='pending_migration', readonly=True, index=True)
    
    status_message = fields.Text(string='Status Message', readonly=True)
    
    odoo19_contract_id = fields.Many2one(
        'amc.contract',
        string='Odoo 19 Contract',
        readonly=True,
        help='Migrated contract in Odoo 19'
    )
    
    migration_date = fields.Datetime(string='Migration Date', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    @api.model
    def action_open_upload_wizard(self):
        """Open the Excel upload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'amc.contract.upload.wizard',
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
            
            # Check for AMC contract migration-specific jobs
            migration_pending = self.env['queue.job'].search_count([
                ('state', '=', 'pending'),
                ('model_name', '=', 'amc.contract.migration.line'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            migration_started = self.env['queue.job'].search_count([
                ('state', '=', 'started'),
                ('model_name', '=', 'amc.contract.migration.line'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            
            _logger.info("📊 Queue status: %s pending (total), %s started (total), %s AMC migration pending, %s AMC migration started", 
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
                    message = f'Queue job cron triggered successfully. {pending_jobs} pending job(s) (including {migration_pending} AMC contract migration jobs) will start processing now.'
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
        """Bulk migrate selected contracts sequentially using Queue Jobs"""
        pending = self.filtered(lambda l: l.status == 'pending_migration')
        if not pending:
            raise UserError('No contracts with "Pending Migration" status selected')
        
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
            raise UserError('No contracts with "Pending Migration" status selected')
        
        # Mark all records as "queued" before enqueueing
        for record in pending:
            record.write({
                'status': 'queued',
                'status_message': 'Queued for migration - waiting to start...',
            })
        self.env.cr.commit()
        _logger.info("✅ Marked %s contracts as 'queued'", len(pending))
        
        # Start sequential migration by enqueueing the first job
        try:
            first_record = self.browse(pending_ids[0])
            first_record.with_delay()._migrate_sequential(pending_ids, 0)
            _logger.info("✅ Started sequential migration for %s contracts", len(pending_ids))
        except AttributeError as e:
            error_msg = str(e)
            _logger.error("Queue Job AttributeError: %s", error_msg, exc_info=True)
            pending.write({
                'status': 'pending_migration',
                'status_message': 'Failed to queue - ' + error_msg,
            })
            self.env.cr.commit()
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
            _logger.error("Queue Job error (%s): %s", error_type, error_msg, exc_info=True)
            pending.write({
                'status': 'pending_migration',
                'status_message': 'Failed to queue - ' + error_msg,
            })
            self.env.cr.commit()
            raise UserError(
                f'Error starting migration: {error_msg}\n\n'
                f'Error type: {error_type}\n'
                f'Please check Odoo logs for more details.'
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Migration Started',
                'message': f'Queued {len(pending_ids)} contracts for sequential migration. You will receive notifications as each completes.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _migrate_sequential(self, record_ids, current_index):
        """
        Sequential migration method using Queue Jobs.
        Migrates one contract at a time, updates status, sends notification, then starts next.
        
        :param record_ids: List of record IDs to migrate
        :param current_index: Current index in the list (0-based)
        """
        if current_index >= len(record_ids):
            _logger.info("Sequential migration completed for all %s records", len(record_ids))
            return
        
        record_id = record_ids[current_index]
        record = self.env['amc.contract.migration.line'].browse(record_id)
        
        if not record.exists():
            _logger.warning("Record %s does not exist, skipping", record_id)
            if current_index + 1 < len(record_ids):
                next_record = record.env['amc.contract.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        contract_number = record.contract_number
        _logger.info("🚀 Starting migration %s/%s: %s (record_id=%s)", current_index + 1, len(record_ids), contract_number, record_id)
        
        if record.status not in ('pending_migration', 'queued'):
            _logger.warning("Record %s is not in pending_migration or queued status (%s), skipping", contract_number, record.status)
            if current_index + 1 < len(record_ids):
                next_record = record.env['amc.contract.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        # Update status to migrating
        record.write({
            'status': 'migrating',
            'status_message': 'Migration in progress...',
        })
        record.env.flush_all()
        _logger.info("📝 Status updated to 'migrating' for %s", contract_number)
        
        try:
            # Check if contract already exists
            existing_contract = record.env['amc.contract'].search([
                ('name', '=', contract_number)
            ], limit=1)
            
            if existing_contract:
                _logger.info("Contract %s already exists in Odoo 19 (ID: %s), marking as migrated", 
                           contract_number, existing_contract.id)
                record.write({
                    'status': 'migrated',
                    'status_message': 'Already migrated (existed in system)',
                    'odoo19_contract_id': existing_contract.id,
                    'migration_date': fields.Datetime.now(),
                    'error_message': False,
                })
                record.env.flush_all()
                self._send_migration_notification(record, 'migrated', 'Already existed in system')
                
                # Continue with next
                if current_index + 1 < len(record_ids):
                    next_record = record.env['amc.contract.migration.line'].browse(record_ids[current_index + 1])
                    if next_record.exists():
                        next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
                return
            
            # Prepare contract values
            contract_vals = record._prepare_contract_vals()
            
            # Create contract
            _logger.info("💾 Creating contract in Odoo 19...")
            contract = record.env['amc.contract'].create(contract_vals)
            _logger.info("✅ Contract created in Odoo 19: %s (ID: %s)", contract.name, contract.id)
            
            record.env.cr.commit()
            
            # Update status to migrated
            record.write({
                'status': 'migrated',
                'status_message': 'Successfully migrated',
                'odoo19_contract_id': contract.id,
                'migration_date': fields.Datetime.now(),
                'error_message': False,
            })
            record.env.flush_all()
            _logger.info("✅ Status updated to 'migrated' for %s", contract_number)
            
            # Send success notification
            self._send_migration_notification(record, 'migrated', 'Successfully migrated', contract.name)
            
            _logger.info("✅ Successfully migrated %s (%s/%s)", contract_number, current_index + 1, len(record_ids))
            
        except Exception as e:
            error_msg = str(e)
            _logger.error("❌ Error migrating contract %s: %s", contract_number, error_msg, exc_info=True)
            
            try:
                record.write({
                    'status': 'error',
                    'status_message': 'Migration failed',
                    'error_message': error_msg[:500] if len(error_msg) > 500 else error_msg,
                })
                record.env.flush_all()
                _logger.info("✅ Status updated to 'error' for %s", contract_number)
            except Exception as status_error:
                _logger.error("❌ Failed to update error status: %s", str(status_error))
            
            try:
                self._send_migration_notification(record, 'error', error_msg)
            except:
                pass
            
            # Log failed migration
            _log_failed_migration(contract_number, error_msg)
        
        # Automatically start next migration
        record.env.flush_all()
        
        if current_index + 1 < len(record_ids):
            next_index = current_index + 1
            next_record_id = record_ids[next_index]
            _logger.info("🔄 Enqueueing next migration (%s/%s): record_id=%s", next_index + 1, len(record_ids), next_record_id)
            
            try:
                fresh_env = record.env
                next_record = fresh_env['amc.contract.migration.line'].browse(next_record_id)
                
                if not next_record.exists():
                    _logger.error("Next record %s does not exist, stopping sequential migration", next_record_id)
                    remaining_ids = record_ids[next_index:]
                    remaining_records = fresh_env['amc.contract.migration.line'].browse(remaining_ids)
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
                    remaining_records = record.env['amc.contract.migration.line'].browse(remaining_ids)
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
    
    def _prepare_contract_vals(self):
        """Prepare contract values from Excel data"""
        self.ensure_one()
        
        # Find customer by name
        customer = False
        if self.customer_name:
            customer = self.env['res.partner'].search([
                ('name', '=', self.customer_name)
            ], limit=1)
            
            if not customer:
                # Try case-insensitive search
                customer = self.env['res.partner'].search([
                    ('name', 'ilike', self.customer_name)
                ], limit=1)
            
            if not customer:
                raise UserError(f'Customer "{self.customer_name}" not found. Please create the customer first.')
        
        # Find stage by status name (e.g., "Confirmed")
        stage = False
        if self.status_name:
            stage = self.env['amc.contract.stage'].search([
                ('name', '=', self.status_name)
            ], limit=1)
            
            if not stage:
                # Default to Draft stage if status not found
                stage = self.env['amc.contract.stage'].search([
                    ('is_default', '=', True),
                    ('name', '=', 'Draft')
                ], limit=1)
                
                if not stage:
                    # Get first stage by sequence
                    stage = self.env['amc.contract.stage'].search([], order='sequence', limit=1)
        else:
            # Default to Draft stage
            stage = self.env['amc.contract.stage'].search([
                ('is_default', '=', True),
                ('name', '=', 'Draft')
            ], limit=1)
            if not stage:
                stage = self.env['amc.contract.stage'].search([], order='sequence', limit=1)
        
        if not stage:
            raise UserError('No contract stage found. Please create at least one stage.')
        
        # Get company from branch mapping if branch_id is provided
        company = False
        if self.odoo14_branch_id:
            # Look up company mapping
            mapping_model = self.env['odoo14.branch.company.mapping']
            company = mapping_model.get_company_for_branch(self.odoo14_branch_id)
            if not company:
                raise UserError(
                    f'Branch ID {self.odoo14_branch_id} is not mapped to any Odoo 19 company. '
                    f'Please create a mapping in "Odoo 14 Migration > Company Mapping" first.'
                )
        else:
            # Use default company if no branch_id provided
            company = self.env.company
        
        # Prepare contract values
        contract_vals = {
            'name': self.contract_number,
            'customer_id': customer.id if customer else False,
            'start_date': self.start_date or False,
            'end_date': self.end_date or False,
            'contract_date': self.contract_date or (self.start_date if self.start_date else fields.Date.today()),
            'contract_value': self.contract_value or 0.0,
            'stage_id': stage.id,
            'branch_id': company.id if company else self.env.company.id,
        }
        
        # Ensure contract_date is not after start_date
        if contract_vals.get('start_date') and contract_vals.get('contract_date'):
            if contract_vals['start_date'] < contract_vals['contract_date']:
                contract_vals['contract_date'] = contract_vals['start_date']
        
        return contract_vals
    
    def _send_migration_notification(self, record, status, message, contract_name=None):
        """Send notification to user about migration status"""
        try:
            user = self.env.user
            
            if status == 'migrated':
                title = '✅ Migration Complete'
                body = 'Contract <strong>%s</strong> has been successfully migrated%s' % (
                    record.contract_number,
                    ' as <strong>%s</strong>' % contract_name if contract_name else ''
                )
            elif status == 'error':
                title = '❌ Migration Failed'
                body = 'Migration failed for contract <strong>%s</strong>: %s' % (record.contract_number, message)
            else:
                title = 'ℹ️ Migration Update'
                body = 'Contract <strong>%s</strong>: %s' % (record.contract_number, message)
            
            _logger.info("📢 Notification: %s - %s", record.contract_number, message)
            
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

