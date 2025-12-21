# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


def _log_failed_crm_lead_migration(lead_name, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        # Get log directory (use module directory/logs)
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_crm_lead_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {lead_name} | {error_detail[:200]}\n")
        
        _logger.info("Failed CRM lead migration logged to: %s", log_file)
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


class CrmLeadMigrationLine(models.Model):
    """Model to store uploaded CRM lead names/IDs and track migration status"""
    _name = 'crm.lead.migration.line'
    _description = 'CRM Lead Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    uploaded_lead_name = fields.Char(
        string='Uploaded Lead Name/ID',
        required=True,
        index=True,
        help='CRM lead name or ID from Excel upload'
    )
    
    in_system_lead_name = fields.Char(
        string='In-System Lead Name',
        readonly=True,
        help='Actual lead name found in Odoo 14 or Odoo 19'
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
    
    odoo14_lead_id = fields.Integer(
        string='Odoo 14 Lead ID',
        readonly=True,
        help='ID of lead in Odoo 14 if found'
    )
    
    odoo19_lead_id = fields.Many2one(
        'crm.lead',
        string='Odoo 19 Lead',
        readonly=True,
        help='Migrated lead in Odoo 19'
    )
    
    migration_date = fields.Datetime(string='Migration Date', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    
    is_opportunity = fields.Boolean(
        string='Opportunity',
        compute='_compute_is_opportunity',
        store=True,
        help='Whether the lead is an opportunity'
    )
    
    @api.depends('odoo19_lead_id', 'odoo19_lead_id.type')
    def _compute_is_opportunity(self):
        """Compute if the lead is an opportunity"""
        for record in self:
            if record.odoo19_lead_id:
                record.is_opportunity = (record.odoo19_lead_id.type == 'opportunity')
            else:
                record.is_opportunity = False

    def check_status(self, lead_name=None, config_id=None):
        """Check status of a CRM lead against Odoo 14 and Odoo 19"""
        self.ensure_one()
        if not lead_name:
            lead_name = self.uploaded_lead_name
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
            # Try by name first
            existing_19 = self.env['crm.lead'].search([
                ('name', '=', lead_name)
            ], limit=1)
            
            # If not found by name, try by ID if lead_name is numeric
            if not existing_19 and lead_name.isdigit():
                existing_19 = self.env['crm.lead'].search([
                    ('id', '=', int(lead_name))
                ], limit=1)
            
            if existing_19:
                return {
                    'status': 'already_migrated',
                    'message': 'Already exists in Odoo 19',
                    'odoo19_id': existing_19.id,
                    'odoo19_name': existing_19.name
                }
            
            # Check in Odoo 14
            # Try by name first
            domain = [('name', '=', lead_name)]
            # If lead_name is numeric, also try by ID
            if lead_name.isdigit():
                domain = ['|', ('id', '=', int(lead_name)), ('name', '=', lead_name)]
            
            try:
                leads = client.search_read(
                    'crm.lead',
                    domain,
                    ['id', 'name'],
                    limit=1
                )
            except:
                # If model doesn't exist, return not found
                return {
                    'status': 'not_found',
                    'message': 'CRM lead model not found in Odoo 14'
                }
            
            if leads:
                return {
                    'status': 'pending_migration',
                    'message': 'Found in Odoo 14, ready to migrate',
                    'odoo14_id': leads[0]['id'],
                    'odoo14_name': leads[0]['name']
                }
            else:
                return {
                    'status': 'not_found',
                    'message': 'Not found in Odoo 14'
                }
                
        except Exception as e:
            _logger.error("Error checking CRM lead status: %s", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def action_check_status(self):
        """Button action to refresh status"""
        for record in self:
            result = record.check_status()
            record.write({
                'status': result.get('status', 'not_found'),
                'status_message': result.get('message', ''),
                'in_system_lead_name': result.get('odoo14_name') or result.get('odoo19_name') or '',
                'odoo14_lead_id': result.get('odoo14_id', 0),
                'odoo19_lead_id': result.get('odoo19_id', False),
            })
    
    @api.model
    def action_open_upload_wizard(self):
        """Open the Excel upload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead.upload.wizard',
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
            
            # Check for CRM lead migration-specific jobs
            migration_pending = self.env['queue.job'].search_count([
                ('state', '=', 'pending'),
                ('model_name', '=', 'crm.lead.migration.line'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            migration_started = self.env['queue.job'].search_count([
                ('state', '=', 'started'),
                ('model_name', '=', 'crm.lead.migration.line'),
                ('method_name', '=', '_migrate_sequential'),
            ])
            
            _logger.info("📊 Queue status: %s pending (total), %s started (total), %s CRM lead migration pending, %s CRM lead migration started", 
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
                    message = f'Queue job cron triggered successfully. {pending_jobs} pending job(s) (including {migration_pending} CRM lead migration jobs) will start processing now.'
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
        """Bulk migrate selected CRM leads sequentially using Queue Jobs"""
        pending = self.filtered(lambda l: l.status == 'pending_migration')
        if not pending:
            raise UserError('No CRM leads with "Pending Migration" status selected')
        
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
            raise UserError('No CRM leads with "Pending Migration" status selected')
        
        # Mark all records as "queued" before enqueueing
        for record in pending:
            record.write({
                'status': 'queued',
                'status_message': 'Queued for migration - waiting to start...',
            })
        self.env.cr.commit()
        _logger.info("✅ Marked %s CRM leads as 'queued'", len(pending))
        
        # Start sequential migration by enqueueing the first job
        try:
            first_record = self.browse(pending_ids[0])
            first_record.with_delay()._migrate_sequential(pending_ids, 0)
            
            _logger.info("✅ Started sequential migration for %s CRM leads", len(pending_ids))
            
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
        
        # Return success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Migration Started',
                'message': f'Queued {len(pending_ids)} CRM leads for sequential migration. You will receive notifications as each completes.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _prepare_lead_vals(self, lead_data, client):
        """Prepare lead values from Odoo 14 data"""
        self.ensure_one()
        
        # Map partner if exists
        partner_id = False
        if lead_data.get('partner_id'):
            if isinstance(lead_data['partner_id'], list) and len(lead_data['partner_id']) > 0:
                partner_14_id = lead_data['partner_id'][0]
                # Find partner in Odoo 19 by name (assuming it was migrated)
                # Try to find by external ID or by searching migrated partners
                partner = self.env['res.partner'].search([
                    ('id', '=', partner_14_id)  # If IDs match (same database)
                ], limit=1)
                if not partner and len(lead_data['partner_id']) > 1:
                    partner_name = lead_data['partner_id'][1]
                    partner = self.env['res.partner'].search([
                        ('name', '=', partner_name)
                    ], limit=1)
                if partner:
                    partner_id = partner.id
        
        # Map user if exists
        user_id = False
        if lead_data.get('user_id'):
            if isinstance(lead_data['user_id'], list) and len(lead_data['user_id']) > 0:
                user_14_id = lead_data['user_id'][0]
                user = self.env['res.users'].search([
                    ('id', '=', user_14_id)
                ], limit=1)
                if not user and len(lead_data['user_id']) > 1:
                    user_name = lead_data['user_id'][1]
                    user = self.env['res.users'].search([
                        ('name', '=', user_name),
                        ('login', '=', user_name.split()[0] if user_name else '')
                    ], limit=1)
                if user:
                    user_id = user.id
        
        # Map team if exists
        team_id = False
        if lead_data.get('team_id'):
            if isinstance(lead_data['team_id'], list) and len(lead_data['team_id']) > 0:
                team_14_id = lead_data['team_id'][0]
                team = self.env['crm.team'].search([
                    ('id', '=', team_14_id)
                ], limit=1)
                if not team and len(lead_data['team_id']) > 1:
                    team_name = lead_data['team_id'][1]
                    team = self.env['crm.team'].search([
                        ('name', '=', team_name)
                    ], limit=1)
                if team:
                    team_id = team.id
        
        # Map stage if exists
        stage_id = False
        if lead_data.get('stage_id'):
            if isinstance(lead_data['stage_id'], list) and len(lead_data['stage_id']) > 0:
                stage_14_id = lead_data['stage_id'][0]
                stage = self.env['crm.stage'].search([
                    ('id', '=', stage_14_id)
                ], limit=1)
                if not stage and len(lead_data['stage_id']) > 1:
                    stage_name = lead_data['stage_id'][1]
                    stage = self.env['crm.stage'].search([
                        ('name', '=', stage_name)
                    ], limit=1)
                if stage:
                    stage_id = stage.id
        
        # Map company if exists
        company_id = False
        if lead_data.get('company_id'):
            if isinstance(lead_data['company_id'], list) and len(lead_data['company_id']) > 0:
                company_14_id = lead_data['company_id'][0]
                company = self.env['res.company'].search([
                    ('id', '=', company_14_id)
                ], limit=1)
                if not company and len(lead_data['company_id']) > 1:
                    company_name = lead_data['company_id'][1]
                    company = self.env['res.company'].search([
                        ('name', '=', company_name)
                    ], limit=1)
                if company:
                    company_id = company.id
        
        # Map state if exists
        state_id = False
        if lead_data.get('state_id'):
            if isinstance(lead_data['state_id'], list) and len(lead_data['state_id']) > 0:
                state_14_id = lead_data['state_id'][0]
                state = self.env['res.country.state'].search([
                    ('id', '=', state_14_id)
                ], limit=1)
                if not state and len(lead_data['state_id']) > 1:
                    state_name = lead_data['state_id'][1]
                    state = self.env['res.country.state'].search([
                        ('name', '=', state_name)
                    ], limit=1)
                if state:
                    state_id = state.id
        
        # Map country if exists
        country_id = False
        if lead_data.get('country_id'):
            if isinstance(lead_data['country_id'], list) and len(lead_data['country_id']) > 0:
                country_14_id = lead_data['country_id'][0]
                country = self.env['res.country'].search([
                    ('id', '=', country_14_id)
                ], limit=1)
                if not country and len(lead_data['country_id']) > 1:
                    country_name = lead_data['country_id'][1]
                    country = self.env['res.country'].search([
                        ('name', '=', country_name)
                    ], limit=1)
                if country:
                    country_id = country.id
        
        # Prepare lead values - include all important fields
        lead_vals = {
            'name': lead_data.get('name', 'Untitled Lead'),
            'partner_id': partner_id,
            'contact_name': lead_data.get('contact_name', False),
            'email_from': lead_data.get('email_from', False),
            'phone': lead_data.get('phone', False),
            'mobile': lead_data.get('mobile', False),
            'street': lead_data.get('street', False),
            'street2': lead_data.get('street2', False),
            'city': lead_data.get('city', False),
            'state_id': state_id,
            'zip': lead_data.get('zip', False),
            'country_id': country_id,
            'user_id': user_id,
            'team_id': team_id,
            'stage_id': stage_id,
            'probability': lead_data.get('probability', 0),
            'type': lead_data.get('type', 'lead'),  # 'lead' or 'opportunity'
            'priority': lead_data.get('priority', '1'),  # '0', '1', '2', '3'
            'expected_revenue': lead_data.get('expected_revenue', 0.0),
            'planned_revenue': lead_data.get('planned_revenue', 0.0),
            'date_deadline': lead_data.get('date_deadline', False),
            'date_open': lead_data.get('date_open', False),
            'date_last_stage_update': lead_data.get('date_last_stage_update', False),
            'date_conversion': lead_data.get('date_conversion', False),
            'date_closed': lead_data.get('date_closed', False),
            'description': lead_data.get('description', False),
            'function': lead_data.get('function', False),
            'title': lead_data.get('title', False),
            'website': lead_data.get('website', False),
            'email_cc': lead_data.get('email_cc', False),
            'phone_state': lead_data.get('phone_state', False),
            'email_state': lead_data.get('email_state', False),
            'is_blacklisted': lead_data.get('is_blacklisted', False),
            'company_id': company_id or self.env.company.id,
        }
        
        # Handle tags - need to create/find tags by name
        tag_ids = []
        if lead_data.get('tag_ids') and isinstance(lead_data['tag_ids'], list):
            for tag_14_id in lead_data['tag_ids']:
                # Try to find tag by ID first, then by name
                tag = self.env['crm.tag'].search([
                    ('id', '=', tag_14_id)
                ], limit=1)
                if tag:
                    tag_ids.append(tag.id)
        
        if tag_ids:
            lead_vals['tag_ids'] = [(6, 0, tag_ids)]
        
        return lead_vals
    
    def action_migrate(self):
        """Migrate this CRM lead from Odoo 14 to Odoo 19"""
        self.ensure_one()
        
        if self.status != 'pending_migration':
            raise UserError('Can only migrate CRM leads with "Pending Migration" status')
        
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
            
            # Get lead data from Odoo 14
            # Try by name first, then by ID if numeric
            domain = [('name', '=', self.uploaded_lead_name)]
            if self.uploaded_lead_name.isdigit():
                domain = ['|', ('id', '=', int(self.uploaded_lead_name)), ('name', '=', self.uploaded_lead_name)]
            
            try:
                leads = client.search_read(
                    'crm.lead',
                    domain,
                    ['id', 'name'],
                    limit=1
                )
            except Exception as e:
                _logger.error("Error searching for lead in Odoo 14: %s", str(e))
                raise UserError(f'Error accessing CRM leads in Odoo 14: {str(e)}')
            
            if not leads:
                self.write({
                    'status': 'not_found',
                    'status_message': 'CRM lead not found in Odoo 14',
                })
                return
            
            lead_data = leads[0]
            
            # Check if lead already exists in Odoo 19
            existing_lead = self.env['crm.lead'].search([
                ('name', '=', lead_data.get('name'))
            ], limit=1)
            
            if existing_lead:
                self.write({
                    'status': 'migrated',
                    'status_message': 'Already migrated (existed in system)',
                    'odoo19_lead_id': existing_lead.id,
                    'in_system_lead_name': existing_lead.name,
                    'migration_date': fields.Datetime.now(),
                    'error_message': False,
                })
                self.env.cr.commit()
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'crm.lead.migration.line',
                    'view_mode': 'list,form',
                    'target': 'current',
                }
            
            # Update status to migrating
            self.write({
                'status': 'migrating',
                'status_message': 'Migration in progress...',
            })
            self.env.cr.commit()
            
            # Get full lead data with all fields
            # Fetch comprehensive field list
            fields_to_fetch = [
                'id', 'name', 'partner_id', 'contact_name', 'email_from', 'phone', 'mobile',
                'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
                'user_id', 'team_id', 'stage_id', 'probability', 'type', 'priority',
                'expected_revenue', 'planned_revenue', 'date_deadline', 'date_open',
                'date_last_stage_update', 'date_conversion', 'date_closed',
                'description', 'function', 'title', 'website', 'email_cc',
                'phone_state', 'email_state', 'is_blacklisted', 'company_id', 'tag_ids',
                'create_date', 'write_date', 'write_uid', 'create_uid'
            ]
            
            try:
                full_lead = client.search_read(
                    'crm.lead',
                    [('id', '=', lead_data['id'])],
                    fields_to_fetch,
                    limit=1
                )
            except Exception as e:
                _logger.warning("Error fetching lead with all fields: %s. Using basic fields.", str(e))
                full_lead = [lead_data]
            
            if not full_lead:
                raise UserError('Could not fetch full CRM lead data')
            
            lead_data = full_lead[0]
            
            # Prepare and create lead
            lead_vals = self._prepare_lead_vals(lead_data, client)
            lead = self.env['crm.lead'].create(lead_vals)
            
            # Preserve original creation date if available
            src_create_date = lead_data.get('create_date')
            if src_create_date:
                try:
                    self.env.cr.execute(
                        """
                        UPDATE crm_lead
                           SET create_date = %s,
                               write_date = COALESCE(write_date, %s)
                         WHERE id = %s
                        """,
                        (src_create_date, src_create_date, lead.id),
                    )
                except Exception as e:
                    _logger.warning("Could not set original create_date: %s", str(e))
            
            self.env.cr.commit()
            
            # Update status to migrated
            self.write({
                'status': 'migrated',
                'status_message': 'Successfully migrated',
                'odoo19_lead_id': lead.id,
                'in_system_lead_name': lead.name,
                'migration_date': fields.Datetime.now(),
                'error_message': False,
            })
            self.env.cr.commit()
            
            # Return to reload list view
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead.migration.line',
                'view_mode': 'list,form',
                'target': 'current',
            }
                
        except UserError:
            raise
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error migrating CRM lead %s: %s", self.uploaded_lead_name, error_msg)
            self.write({
                'status': 'error',
                'status_message': 'Migration failed',
                'error_message': error_msg,
            })
            self.env.cr.commit()
            # Log failed migration for later processing
            _log_failed_crm_lead_migration(self.uploaded_lead_name, error_msg)
            raise UserError('Migration failed: %s' % error_msg)
    
    def _migrate_sequential(self, record_ids, current_index):
        """
        Sequential migration method using Queue Jobs.
        Migrates one CRM lead at a time, updates status, sends notification, then starts next.
        
        :param record_ids: List of record IDs to migrate
        :param current_index: Current index in the list (0-based)
        """
        if current_index >= len(record_ids):
            _logger.info("Sequential migration completed for all %s records", len(record_ids))
            return
        
        record_id = record_ids[current_index]
        record = self.env['crm.lead.migration.line'].browse(record_id)
        
        if not record.exists():
            _logger.warning("Record %s does not exist, skipping", record_id)
            if current_index + 1 < len(record_ids):
                next_record = record.env['crm.lead.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        lead_name = record.uploaded_lead_name
        _logger.info("🚀 Starting migration %s/%s: %s (record_id=%s)", current_index + 1, len(record_ids), lead_name, record_id)
        
        if record.status not in ('pending_migration', 'queued'):
            _logger.warning("Record %s is not in pending_migration or queued status (%s), skipping", lead_name, record.status)
            if current_index + 1 < len(record_ids):
                next_record = record.env['crm.lead.migration.line'].browse(record_ids[current_index + 1])
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
                next_record = record.env['crm.lead.migration.line'].browse(record_ids[current_index + 1])
                if next_record.exists():
                    next_record.with_delay()._migrate_sequential(record_ids, current_index + 1)
            return
        
        # Update status to migrating
        record.write({
            'status': 'migrating',
            'status_message': 'Migration in progress...',
        })
        record.env.flush_all()
        _logger.info("📝 Status updated to 'migrating' for %s", lead_name)
        
        # Wrap entire migration in try-except
        try:
            # Call action_migrate for this record
            record.action_migrate()
            
            _logger.info("✅ Successfully migrated %s (%s/%s)", lead_name, current_index + 1, len(record_ids))
            
        except Exception as e:
            error_msg = str(e)
            _logger.error("❌ Error migrating CRM lead %s: %s", lead_name, error_msg, exc_info=True)
            
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
                next_record = fresh_env['crm.lead.migration.line'].browse(next_record_id)
                
                if not next_record.exists():
                    _logger.error("Next record %s does not exist, stopping sequential migration", next_record_id)
                    remaining_ids = record_ids[next_index:]
                    remaining_records = fresh_env['crm.lead.migration.line'].browse(remaining_ids)
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
                    remaining_records = record.env['crm.lead.migration.line'].browse(remaining_ids)
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
    
    def action_bulk_convert_to_opportunity(self):
        """Bulk convert selected CRM leads to opportunities"""
        # Get records with valid CRM leads
        records_with_leads = self.filtered(lambda r: r.odoo19_lead_id and r.status in ('migrated', 'already_migrated'))
        
        if not records_with_leads:
            raise UserError('No leads selected or no CRM leads found to convert. Please select records with migrated CRM leads.')
        
        converted_count = 0
        already_opportunities = 0
        errors = []
        
        for record in records_with_leads:
            try:
                lead = record.odoo19_lead_id
                
                # Check if already an opportunity
                if lead.type == 'opportunity':
                    already_opportunities += 1
                    _logger.info(f"Lead '{lead.name}' (ID: {lead.id}) is already an opportunity")
                    continue
                
                # Convert to opportunity
                lead.write({'type': 'opportunity'})
                converted_count += 1
                _logger.info(f"Converted lead '{lead.name}' (ID: {lead.id}) to opportunity")
                
            except Exception as e:
                error_msg = str(e)
                errors.append(f"Lead '{record.uploaded_lead_name}': {error_msg}")
                _logger.error(f"Error converting lead '{record.uploaded_lead_name}' to opportunity: {error_msg}", exc_info=True)
        
        # Prepare message
        message_parts = []
        if converted_count > 0:
            message_parts.append(f'{converted_count} lead(s) converted to opportunity')
        if already_opportunities > 0:
            message_parts.append(f'{already_opportunities} lead(s) were already opportunities')
        if errors:
            message_parts.append(f'{len(errors)} error(s) occurred')
        
        message = '. '.join(message_parts) if message_parts else 'No leads were converted'
        
        notification_type = 'success' if converted_count > 0 and not errors else 'warning' if errors else 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Convert to Opportunity',
                'message': message,
                'type': notification_type,
                'sticky': False,
            }
        }
    
    def _send_migration_notification(self, record, status, message, lead_name=None):
        """Send notification to user about migration status"""
        try:
            user = self.env.user
            
            if status == 'migrated':
                title = '✅ Migration Complete'
                body = 'CRM Lead <strong>%s</strong> has been successfully migrated%s' % (
                    record.uploaded_lead_name,
                    ' as <strong>%s</strong>' % lead_name if lead_name else ''
                )
            elif status == 'error':
                title = '❌ Migration Failed'
                body = 'Migration failed for CRM lead <strong>%s</strong>: %s' % (record.uploaded_lead_name, message)
            else:
                title = 'ℹ️ Migration Update'
                body = 'CRM Lead <strong>%s</strong>: %s' % (record.uploaded_lead_name, message)
            
            _logger.info("📢 Notification: %s - %s", record.uploaded_lead_name, message)
            
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

