# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)


class EmployeePreview(models.TransientModel):
    _name = 'odoo14.employee.preview'
    _description = 'Odoo 14 Employee Preview'

    wizard_id = fields.Many2one(
        'odoo14.employee.migration.wizard',
        string='Migration Wizard',
        required=True,
        ondelete='cascade'
    )
    
    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=True
    )
    
    current_index = fields.Integer(string='Current Index', default=0)
    total_count = fields.Integer(string='Total Count', default=0)
    
    display_position = fields.Char(string='Position', compute='_compute_display_position', readonly=True)
    
    @api.depends('current_index', 'total_count')
    def _compute_display_position(self):
        for record in self:
            if record.current_index is not False and record.total_count:
                record.display_position = 'Employee %s of %s' % (record.current_index + 1, record.total_count)
            else:
                record.display_position = ''
    
    # Employee basic fields
    employee_name = fields.Char(string='Name', readonly=True)
    employee_work_email = fields.Char(string='Work Email', readonly=True)
    employee_work_phone = fields.Char(string='Work Phone', readonly=True)
    employee_mobile_phone = fields.Char(string='Mobile Phone', readonly=True)
    employee_job = fields.Char(string='Job Position', readonly=True)
    employee_department = fields.Char(string='Department', readonly=True)
    employee_company = fields.Char(string='Company', readonly=True)
    employee_user = fields.Char(string='Related User', readonly=True)
    employee_active = fields.Boolean(string='Active', readonly=True)
    employee_image = fields.Binary(string='Photo', readonly=True)
    
    # Full employee data (JSON) to show all fields including custom fields
    employee_data_json = fields.Text(string='Full Employee Data (JSON)', readonly=True)
    
    def _load_employee(self, offset=0):
        """Load employee data from Odoo 14"""
        self.ensure_one()
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14.')
            
            # Get all available fields dynamically
            default_fields = [
                'name', 'work_email', 'work_phone', 'mobile_phone', 'job_id', 
                'department_id', 'company_id', 'user_id', 'active'
            ]
            
            # Image fields
            image_fields = ['image_1920', 'image_1024', 'image_512', 'image_256', 'image_128']
            
            fields_to_fetch = default_fields.copy()
            
            # Try to get all fields including custom fields
            try:
                all_fields = client.fields_get('hr.employee')
                if all_fields:
                    # Add image fields if they exist
                    for img_field in image_fields:
                        if img_field in all_fields:
                            fields_to_fetch.append(img_field)
                    
                    # Add all other fields (including custom fields)
                    # Skip attendance-related fields (user doesn't want attendance data)
                    skip_field_names = [
                        'employee_type',  # Doesn't exist in Odoo 14
                        'attendance_ids',  # Attendance data - skip
                        'attendance_state',  # Attendance state - skip
                        'last_attendance_id',  # Last attendance - skip
                        'attendance_manager_id',  # Attendance manager - skip
                    ]
                    for f, field_info in all_fields.items():
                        field_type = field_info.get('type', '')
                        # Skip relational fields except Many2one
                        if field_type in ('one2many', 'many2many'):
                            continue
                        # Skip system fields
                        if f.startswith('__') or f in ['id', 'create_uid', 'write_uid', 'create_date', 'write_date']:
                            continue
                        # Skip attendance-related and other unwanted fields
                        if f in skip_field_names or 'attendance' in f.lower():
                            continue
                        if f not in fields_to_fetch:
                            fields_to_fetch.append(f)
            except Exception as e:
                _logger.warning("Could not get all fields, using default set: %s", str(e))
            
            # Get employee at offset
            domain = []
            employees = client.search_read('hr.employee', domain, 
                fields_to_fetch, 
                limit=1, offset=offset)
            
            if not employees:
                raise UserError('No employee found at this position.')
            
            employee = employees[0]
            
            # Extract Many2one field values
            job_name = ''
            if employee.get('job_id'):
                job_data = employee.get('job_id')
                if isinstance(job_data, (list, tuple)) and len(job_data) > 1:
                    job_name = job_data[1]
            
            dept_name = ''
            if employee.get('department_id'):
                dept_data = employee.get('department_id')
                if isinstance(dept_data, (list, tuple)) and len(dept_data) > 1:
                    dept_name = dept_data[1]
            
            company_name = ''
            if employee.get('company_id'):
                company_data = employee.get('company_id')
                if isinstance(company_data, (list, tuple)) and len(company_data) > 1:
                    company_name = company_data[1]
            
            user_name = ''
            if employee.get('user_id'):
                user_data = employee.get('user_id')
                if isinstance(user_data, (list, tuple)) and len(user_data) > 1:
                    user_name = user_data[1]
            
            # Get image (prefer largest available)
            employee_image = False
            for img_field in ['image_1920', 'image_1024', 'image_512', 'image_256', 'image_128']:
                if employee.get(img_field):
                    employee_image = employee.get(img_field)
                    break
            
            # Format JSON data nicely
            employee_json = json.dumps(employee, indent=2, default=str)
            
            # Update preview with employee data
            self.write({
                'current_index': offset,
                'employee_name': employee.get('name', ''),
                'employee_work_email': employee.get('work_email', ''),
                'employee_work_phone': employee.get('work_phone', ''),
                'employee_mobile_phone': employee.get('mobile_phone', ''),
                'employee_job': job_name,
                'employee_department': dept_name,
                'employee_company': company_name,
                'employee_user': user_name,
                'employee_active': employee.get('active', True),
                'employee_image': employee_image,
                'employee_data_json': employee_json,
            })
            
            return True
        except Exception as e:
            _logger.error("Error loading employee: %s" % str(e))
            raise UserError('Error loading employee: %s' % str(e))
    
    def action_previous(self):
        """Navigate to previous employee"""
        self.ensure_one()
        if self.current_index <= 0:
            raise UserError('This is the first employee.')
        
        new_index = self.current_index - 1
        self._load_employee(offset=new_index)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee Preview (%s of %s)' % (self.current_index + 1, self.total_count),
            'res_model': 'odoo14.employee.preview',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }
    
    def action_next(self):
        """Navigate to next employee"""
        self.ensure_one()
        if self.current_index >= self.total_count - 1:
            raise UserError('This is the last employee.')
        
        new_index = self.current_index + 1
        self._load_employee(offset=new_index)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee Preview (%s of %s)' % (self.current_index + 1, self.total_count),
            'res_model': 'odoo14.employee.preview',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }
