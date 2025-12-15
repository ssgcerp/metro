# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import ast

_logger = logging.getLogger(__name__)


class EmployeeMigrationWizard(models.TransientModel):
    _name = 'odoo14.employee.migration.wizard'
    _description = 'Employee Migration Wizard'

    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=True,
        help='Select the Odoo 14 connection configuration'
    )
    
    # Employee migration fields
    employees_count = fields.Integer(string='Employees Total Count', default=0, readonly=True)
    employees_migrated = fields.Integer(string='Employees Migrated', default=0, readonly=True)
    employees_progress = fields.Float(string='Employees Progress %', compute='_compute_employees_progress', store=False)
    
    migration_status = fields.Text(string='Migration Status', readonly=True)
    is_migrating = fields.Boolean(string='Migration in Progress', default=False, readonly=True)
    
    @api.depends('employees_count', 'employees_migrated')
    def _compute_employees_progress(self):
        for record in self:
            if record.employees_count > 0:
                record.employees_progress = (record.employees_migrated / record.employees_count) * 100
            else:
                record.employees_progress = 0.0
    
    def action_check_employees(self):
        """Check employees count"""
        return self._check_model('employees', 'hr.employee', "[]")
    
    def _check_model(self, model_type, model_name, domain_str):
        """Check count for a specific model"""
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
            
            # Parse domain string
            if domain_str:
                try:
                    domain = ast.literal_eval(domain_str)
                except:
                    try:
                        import json
                        domain = json.loads(domain_str.replace("'", '"'))
                    except:
                        domain = []
            else:
                domain = []
            
            # Get count using count method
            try:
                count = client.count(model_name, domain)
                _logger.info("XML-RPC count for %s with domain %s: %s" % (model_name, domain, count))
            except Exception as e:
                error_str = str(e)
                _logger.error("Error getting count via XML-RPC for %s: %s" % (model_name, error_str))
                # Try without domain as fallback
                try:
                    _logger.info("Trying without domain...")
                    count = client.count(model_name, [])
                    _logger.info("XML-RPC count for %s without domain: %s" % (model_name, count))
                except Exception as e2:
                    _logger.error("Error even without domain: %s" % str(e2))
                    raise UserError('Failed to get count for %s: %s' % (model_name, str(e)))
            
            # Update the count field
            field_name = f'{model_type}_count'
            self.write({field_name: count})
            
            # Commit the transaction to ensure data is saved
            self.env.cr.commit()
            
            # Log the update
            _logger.info("Updated %s to %s for wizard ID %s" % (field_name, count, self.id))
            
            # Return action to reload the form so buttons become visible when count > 0
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'views': [(False, 'form')],
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error checking %s: %s" % (model_type, str(e)))
            raise UserError('Error checking %s: %s' % (model_type, str(e)))
    
    def action_preview_employees(self):
        """Preview employees"""
        self.ensure_one()
        if self.employees_count == 0:
            raise UserError('No employees found. Please check data first.')
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        try:
            # Create preview record
            preview = self.env['odoo14.employee.preview'].create({
                'wizard_id': self.id,
                'config_id': self.config_id.id,
                'current_index': 0,
                'total_count': self.employees_count,
            })
            
            # Load first employee
            preview._load_employee(offset=0)
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'odoo14.employee.preview',
                'res_id': preview.id,
                'view_mode': 'form',
                'target': 'new',
                'name': 'Employee Preview (%s of %s)' % (1, self.employees_count),
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error previewing employees: %s" % str(e))
            raise UserError('Error previewing employees: %s' % str(e))
    
    def action_migrate_employees(self):
        """Migrate employees from Odoo 14 to Odoo 19"""
        self.ensure_one()
        if self.employees_count == 0:
            raise UserError('No employees found. Please check data first.')
        
        if not self.config_id:
            raise UserError('Please select a migration configuration first.')
        
        # Check if we're resuming migration or starting new
        offset = self.employees_migrated  # Resume from where we left off
        
        # Set migration in progress flag (if not already set)
        if not self.is_migrating:
            self.write({
                'is_migrating': True,
                'migration_status': f'Starting migration... (Resuming from {offset})' if offset > 0 else 'Starting migration...',
            })
            self.env.cr.commit()
        
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
            
            # Get standard employee fields (excluding employee_type which doesn't exist in Odoo 14)
            default_fields = [
                'name', 'work_email', 'work_phone', 'mobile_phone', 'job_id', 
                'department_id', 'company_id', 'user_id', 'active'
            ]
            
            fields_to_fetch = default_fields.copy()
            
            try:
                all_fields = client.fields_get('hr.employee')
                if all_fields:
                    # Image fields to include (for photo migration) - only if they exist
                    image_fields = ['image_1920', 'image_1024', 'image_512', 'image_256', 'image_128']
                    for img_field in image_fields:
                        if img_field in all_fields:
                            fields_to_fetch.append(img_field)
                    
                    # Add other fields dynamically
                    dynamic_fields = []
                    # Fields to skip (attendance and other unwanted data)
                    skip_field_names = [
                        'employee_type',  # Doesn't exist in Odoo 14
                        'attendance_ids',  # Attendance data - skip during migration
                        'attendance_state',  # Attendance state - skip
                        'last_attendance_id',  # Last attendance - skip
                        'attendance_manager_id',  # Attendance manager - skip
                    ]
                    for f, field_info in all_fields.items():
                        field_type = field_info.get('type', '')
                        # Skip relational fields except Many2one
                        if field_type in ('one2many', 'many2many'):
                            continue
                        # Include all other fields that aren't already in our list
                        if f not in fields_to_fetch:
                            # Skip system/internal fields
                            if f.startswith('__') or f in ['id', 'create_uid', 'write_uid', 'create_date', 'write_date']:
                                continue
                            # Skip attendance-related and other unwanted fields
                            if f in skip_field_names or 'attendance' in f.lower():
                                _logger.debug("Skipping attendance field: %s", f)
                                continue
                            dynamic_fields.append(f)
                    fields_to_fetch = list(set(fields_to_fetch + dynamic_fields))
                    _logger.info("Retrieved %s fields for hr.employee migration (including image fields)", len(fields_to_fetch))
            except Exception as e:
                _logger.warning("Could not get all fields for migration using fields_get, using default set: %s", str(e))
            
            batch_size = 20
            
            employees = client.search_read(
                'hr.employee',
                [],
                fields_to_fetch,
                limit=batch_size,
                offset=offset,
                order='id'
            )
            
            if not employees:
                self.write({
                    'is_migrating': False,
                    'migration_status': 'Migration complete! All employees migrated.',
                })
                self.env.cr.commit()
                return self.action_refresh_view(notification_message='All employees have been migrated.')
            
            migrated = 0
            skipped = 0
            errors = 0
            
            self.write({
                'migration_status': f'Migrating batch... ({offset}/{self.employees_count})',
            })
            self.env.cr.commit()
            
            for employee_data in employees:
                try:
                    employee_name = employee_data.get('name', '').strip()
                    
                    if employee_name:
                        # Check for duplicates by name
                        existing = self.env['hr.employee'].search([
                            ('name', '=', employee_name)
                        ], limit=1)
                        
                        if existing:
                            skipped += 1
                            _logger.info("Skipping duplicate employee: %s", employee_name)
                            continue
                    
                    # Create employee with all details
                    employee_vals = self._prepare_employee_vals(employee_data, client)
                    self.env['hr.employee'].create(employee_vals)
                    
                    self.env.cr.commit()
                    migrated += 1
                    
                    current_total = offset + migrated
                    progress_percent = (current_total / self.employees_count * 100) if self.employees_count > 0 else 0
                    progress_vals = {
                        'employees_migrated': current_total,
                        'migration_status': f'Migrating... ({current_total}/{self.employees_count}) - {progress_percent:.1f}%',
                    }
                    self.write(progress_vals)
                    self.env.cr.commit()
                    _logger.info("Progress: Migrated %s/%s employees (%.1f%%)", current_total, self.employees_count, progress_percent)
                    
                except Exception as e:
                    try:
                        if not self.env.cr.closed:
                            self.env.cr.rollback()
                    except Exception as rollback_error:
                        _logger.error("Error during rollback: %s", str(rollback_error))
                        try:
                            self.env.registry.clear_cache()
                        except Exception:
                            pass
                    
                    errors += 1
                    _logger.error("Error migrating employee %s: %s", employee_data.get('name', 'Unknown'), str(e))
                    continue
            
            current_total = offset + migrated
            progress_percent = (current_total / self.employees_count * 100) if self.employees_count > 0 else 0
            
            if current_total >= self.employees_count:
                self.write({
                    'employees_migrated': current_total,
                    'is_migrating': False,
                    'migration_status': f'Migration complete! Migrated: {current_total}, Skipped: {skipped}, Errors: {errors}',
                })
                self.env.cr.commit()
                
                message = f'Migration complete! Migrated: {current_total}, Skipped (duplicates): {skipped}, Errors: {errors}'
                return self.action_refresh_view(notification_message=message)
            
            # Ensure is_migrating is still True to continue
            self.write({
                'employees_migrated': current_total,
                'is_migrating': True,  # Ensure flag is set for auto-continue
                'migration_status': f'Migrated batch: {current_total}/{self.employees_count} ({progress_percent:.1f}%) - Continuing...',
            })
            self.env.cr.commit()
            _logger.info("Batch complete: %s/%s employees migrated. Returning view reload action for auto-continue.", current_total, self.employees_count)
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'views': [(False, 'form')],
            }
        
        except UserError:
            raise
        except Exception as e:
            self.write({
                'is_migrating': False,
                'migration_status': f'Migration error: {str(e)}',
            })
            self.env.cr.commit()
            _logger.error("Error migrating employees: %s", str(e))
            raise UserError('Error migrating employees: %s' % str(e))
    
    def _prepare_employee_vals(self, employee_data, client):
        """Prepare employee values for creation"""
        employee_vals = {
            'name': employee_data.get('name', ''),
            'work_email': employee_data.get('work_email', False),
            'work_phone': employee_data.get('work_phone', False),
            'mobile_phone': employee_data.get('mobile_phone', False),
            'active': employee_data.get('active', True),
        }
        
        # Handle image fields (photos) - migrate all available image sizes
        image_fields = ['image_1920', 'image_1024', 'image_512', 'image_256', 'image_128']
        for img_field in image_fields:
            if employee_data.get(img_field):
                # Image data comes as base64 encoded string
                employee_vals[img_field] = employee_data[img_field]
        
        # Handle job_id (Many2one)
        if employee_data.get('job_id'):
            job_id = employee_data['job_id']
            if isinstance(job_id, (list, tuple)) and len(job_id) > 0:
                job_name = job_id[1] if len(job_id) > 1 else str(job_id[0])
                job = self.env['hr.job'].search([('name', '=', job_name)], limit=1)
                if job:
                    employee_vals['job_id'] = job.id
                else:
                    _logger.warning("Job not found: %s", job_name)
        
        # Handle department_id (Many2one)
        if employee_data.get('department_id'):
            dept_id = employee_data['department_id']
            if isinstance(dept_id, (list, tuple)) and len(dept_id) > 0:
                dept_name = dept_id[1] if len(dept_id) > 1 else str(dept_id[0])
                dept = self.env['hr.department'].search([('name', '=', dept_name)], limit=1)
                if dept:
                    employee_vals['department_id'] = dept.id
                else:
                    _logger.warning("Department not found: %s", dept_name)
        
        # Handle company_id (Many2one)
        if employee_data.get('company_id'):
            company_id = employee_data['company_id']
            if isinstance(company_id, (list, tuple)) and len(company_id) > 0:
                company_name = company_id[1] if len(company_id) > 1 else str(company_id[0])
                company = self.env['res.company'].search([('name', '=', company_name)], limit=1)
                if company:
                    employee_vals['company_id'] = company.id
                else:
                    _logger.warning("Company not found: %s", company_name)
        
        # Handle user_id (Many2one) - skip if not exists
        if employee_data.get('user_id'):
            user_id = employee_data['user_id']
            if isinstance(user_id, (list, tuple)) and len(user_id) > 0:
                user_login = user_id[1] if len(user_id) > 1 else str(user_id[0])
                user = self.env['res.users'].search([('login', '=', user_login)], limit=1)
                if user:
                    employee_vals['user_id'] = user.id
                else:
                    _logger.warning("User not found: %s", user_login)
        
        # Copy ALL other fields from Odoo 14 (including custom fields)
        # This ensures complete migration of all employee data
        # Skip attendance-related fields - user doesn't want attendance data migrated
        skip_fields = ['id', 'create_uid', 'write_uid', 'create_date', 'write_date', 
                      'employee_type', 'job_id', 'department_id', 'company_id', 'user_id',
                      'name', 'work_email', 'work_phone', 'mobile_phone', 'active',
                      'attendance_ids', 'attendance_state', 'last_attendance_id', 'attendance_manager_id'] + image_fields
        
        # Get Odoo 19 hr.employee model fields
        odoo19_fields = self.env['hr.employee']._fields
        
        for field_name, field_value in employee_data.items():
            # Skip already handled fields and system fields
            if field_name in skip_fields:
                continue
            
            # Skip attendance-related fields (user doesn't want attendance data)
            if 'attendance' in field_name.lower():
                _logger.debug("Skipping attendance field during migration: %s", field_name)
                continue
            
            # Skip empty values (but allow False/0 for boolean/integer fields)
            if field_value in (None, '') and field_name not in odoo19_fields:
                continue
            
            # Check if field exists in Odoo 19 model
            if field_name in odoo19_fields:
                field = odoo19_fields[field_name]
                
                # Handle different field types
                if field.type == 'many2one':
                    # Already handled above for specific fields, skip others
                    continue
                elif field.type == 'one2many' or field.type == 'many2many':
                    # Skip relational fields (too complex to migrate automatically)
                    continue
                elif field.type == 'binary':
                    # Copy binary fields (images, attachments, etc.)
                    employee_vals[field_name] = field_value
                elif field.type in ('char', 'text', 'integer', 'float', 'boolean', 'date', 'datetime', 'selection', 'monetary'):
                    # Copy simple field types
                    employee_vals[field_name] = field_value
                else:
                    # Try to copy other field types
                    try:
                        employee_vals[field_name] = field_value
                    except Exception as e:
                        _logger.warning("Could not copy field %s (type: %s): %s", field_name, field.type, str(e))
            else:
                # Field doesn't exist in Odoo 19 - log it for reference
                _logger.debug("Field %s from Odoo 14 does not exist in Odoo 19 hr.employee model", field_name)
        
        return employee_vals
    
    def action_refresh_view(self, notification_message=None):
        """Refresh the view to show updated progress and optionally display a notification"""
        action = {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
        }
        if notification_message:
            action['effect'] = {
                'fadeout': 'slow',
                'message': notification_message,
                'type': 'rainbow_man',
            }
        return action
