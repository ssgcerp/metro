# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


def _log_failed_project_migration(project_code, error_detail):
    """Log failed migration to a file for later processing"""
    try:
        # Get log directory (use module directory/logs)
        module_dir = os.path.dirname(os.path.dirname(__file__))
        log_dir = os.path.join(module_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'failed_project_migrations.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} | {project_code} | {error_detail[:200]}\n")
        
        _logger.info("Failed project migration logged to: %s", log_file)
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


class ProjectMigrationLine(models.Model):
    """Model to store uploaded Project data from Excel and track migration status"""
    _name = 'project.migration.line'
    _description = 'Project Migration Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # Excel Data Fields
    project_code = fields.Char(
        string='Project Code',
        required=True,
        index=True,
        help='Project code from Excel'
    )
    
    name = fields.Char(
        string='Name',
        help='Project name from Excel'
    )
    
    project_manager_name = fields.Char(
        string='Project Manager (Excel)',
        help='Project Manager name from Excel'
    )
    
    customer_name = fields.Char(
        string='Customer (Excel)',
        help='Customer name from Excel'
    )
    
    sales_man_name = fields.Char(
        string='Sales Man (Excel)',
        help='Sales Man name from Excel'
    )
    
    is_amc = fields.Char(
        string='Is Amc (Excel)',
        help='Is Amc value from Excel'
    )
    
    status_name = fields.Char(
        string='Status (Excel)',
        help='Status from Excel'
    )
    
    company_name = fields.Char(
        string='Company (Excel)',
        help='Company name from Excel'
    )
    
    is_amc_project = fields.Char(
        string='Is AMC Project (Excel)',
        help='Is AMC Project value from Excel'
    )
    
    # Migration Fields
    status = fields.Selection([
        ('pending_migration', 'Pending Migration'),
        ('queued', 'Queued'),
        ('migrating', 'Migrating'),
        ('migrated', 'Migrated'),
        ('error', 'Error'),
    ], string='Migration Status', default='pending_migration', readonly=True, index=True, tracking=True)
    
    status_message = fields.Text(string='Status Message', readonly=True)
    
    odoo19_project_id = fields.Many2one(
        'project.project',
        string='Odoo 19 Project',
        readonly=True,
        help='Migrated project in Odoo 19'
    )
    
    migration_date = fields.Datetime(string='Migration Date', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    @api.model
    def action_open_upload_wizard(self):
        """Open the Excel upload wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': 'Upload Excel',
        }

    def action_bulk_migrate(self):
        """Bulk migrate selected projects - only sets status to Queued"""
        try:
            pending = self.filtered(lambda l: l.status == 'pending_migration')
            if not pending:
                raise UserError('No projects with "Pending Migration" status selected')

            pending_ids = pending.ids

            # Mark all records as "queued" before enqueueing
            fresh_pending = self.env['project.migration.line'].browse(pending_ids)
            for record in fresh_pending:
                record.write({
                    'status': 'queued',
                    'status_message': 'Queued for migration - waiting to be processed...',
                    'error_message': False,  # Clear any previous error messages
                })
            self.env.cr.commit()
            _logger.info("✅ Marked %s projects as 'queued'", len(fresh_pending))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Projects Queued',
                    'message': f'Queued {len(pending_ids)} projects for migration. Use PowerShell script or HTTP route to start processing.',
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
                fresh_pending = self.env['project.migration.line'].browse(pending_ids)
                fresh_pending.write({
                    'status': 'pending_migration',
                    'status_message': f'Failed to queue (unexpected error): {error_msg[:200]}',
                    'error_message': error_msg[:500],
                })
                self.env.cr.commit()
            raise UserError(f'An unexpected error occurred while queuing projects: {error_msg}')

    def action_migrate(self):
        """Migrate project from Excel data to Odoo 19"""
        self.ensure_one()
        
        if self.status == 'migrated':
            raise UserError('This project has already been migrated')
        
        try:
            # Mark as migrating
            self.write({
                'status': 'migrating',
                'status_message': 'Starting migration...',
                'error_message': False,
            })
            self.env.cr.commit()
            
            # Find or create customer
            customer = False
            if self.customer_name:
                customer = self.env['res.partner'].search([
                    ('name', '=', self.customer_name)
                ], limit=1)
                
                if not customer:
                    customer = self.env['res.partner'].search([
                        ('name', 'ilike', self.customer_name)
                    ], limit=1)
                
                if not customer:
                    raise UserError(f'Customer "{self.customer_name}" not found')
            
            # Find company
            company = False
            if self.company_name:
                company = self.env['res.company'].search([
                    ('name', 'ilike', self.company_name)
                ], limit=1)
            
            if not company:
                company = self.env.company
            
            # Find project manager (from Employees/Users)
            project_manager = False
            if self.project_manager_name:
                # Try to find by employee name
                employee = self.env['hr.employee'].search([
                    ('name', '=', self.project_manager_name)
                ], limit=1)
                
                if not employee:
                    employee = self.env['hr.employee'].search([
                        ('name', 'ilike', self.project_manager_name)
                    ], limit=1)
                
                if employee and employee.user_id:
                    project_manager = employee.user_id
                else:
                    # Try to find by user name
                    project_manager = self.env['res.users'].search([
                        ('name', '=', self.project_manager_name)
                    ], limit=1)
                    
                    if not project_manager:
                        project_manager = self.env['res.users'].search([
                            ('name', 'ilike', self.project_manager_name)
                        ], limit=1)
            
            # Find sales man (from Employees/Users)
            sales_man = False
            if self.sales_man_name:
                # Try to find by employee name
                employee = self.env['hr.employee'].search([
                    ('name', '=', self.sales_man_name)
                ], limit=1)
                
                if not employee:
                    employee = self.env['hr.employee'].search([
                        ('name', 'ilike', self.sales_man_name)
                    ], limit=1)
                
                if employee and employee.user_id:
                    sales_man = employee.user_id
                else:
                    # Try to find by user name
                    sales_man = self.env['res.users'].search([
                        ('name', '=', self.sales_man_name)
                    ], limit=1)
                    
                    if not sales_man:
                        sales_man = self.env['res.users'].search([
                            ('name', 'ilike', self.sales_man_name)
                        ], limit=1)
            
            # Find stage by status name
            stage = False
            if self.status_name:
                stage = self.env['fc.project.stage'].search([
                    ('name', '=', self.status_name)
                ], limit=1)
            
            if not stage:
                # Get default stage
                stage = self.env['fc.project.stage'].search([
                    ('is_draft_stage', '=', True),
                    ('active', '=', True)
                ], limit=1)
                
                if not stage:
                    stage = self.env['fc.project.stage'].search([
                        ('sequence', '=', 10),
                        ('active', '=', True)
                    ], limit=1)
            
            # Parse boolean fields
            is_amc = False
            if self.is_amc:
                is_amc_str = str(self.is_amc).strip().lower()
                is_amc = is_amc_str in ('true', 'yes', '1', 'y')
            
            is_amc_project = False
            if self.is_amc_project:
                is_amc_project_str = str(self.is_amc_project).strip().lower()
                is_amc_project = is_amc_project_str in ('true', 'yes', '1', 'y')
            
            # Check if project with this project_code already exists
            existing_project = self.env['project.project'].search([
                ('project_code', '=', self.project_code)
            ], limit=1)
            
            if existing_project:
                # Project already exists, skip creation
                _logger.info("Project %s already exists (ID: %s), skipping creation", self.project_code, existing_project.id)
                project = existing_project
                status_message = f'Project already exists in Odoo 19 - skipped creation'
            else:
                # Prepare project values
                project_vals = {
                    'name': self.name or self.project_code,
                    'project_code': self.project_code,
                    'partner_id': customer.id if customer else False,
                    'company_id': company.id,
                    'user_id': project_manager.id if project_manager else False,
                    'stage_id': stage.id if stage else False,
                    'is_amc': is_amc,
                    'is_amc_project': is_amc_project,
                }
                
                # Create project
                project = self.env['project.project'].create(project_vals)
                _logger.info("Created project %s (ID: %s)", project.name, project.id)
                status_message = f'Successfully migrated to Odoo 19'
            
            # Update status
            self.write({
                'status': 'migrated',
                'status_message': status_message,
                'odoo19_project_id': project.id,
                'migration_date': fields.Datetime.now(),
            })
            self.env.cr.commit()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Migration Complete',
                    'message': f'Project "{project.name}" migrated successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except UserError:
            raise
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error migrating project: %s", error_msg, exc_info=True)
            _log_failed_project_migration(self.project_code, error_msg)
            
            self.write({
                'status': 'error',
                'status_message': f'Migration failed: {error_msg[:200]}',
                'error_message': error_msg[:500],
            })
            self.env.cr.commit()
            
            raise UserError(f'Error migrating project: {error_msg}')

