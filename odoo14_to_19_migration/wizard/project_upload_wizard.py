# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import base64
import io
import json

try:
    from openpyxl import load_workbook, Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    Workbook = None

_logger = logging.getLogger(__name__)


class ProjectUploadWizard(models.TransientModel):
    """Wizard for uploading Excel file with Project data"""
    _name = 'project.upload.wizard'
    _description = 'Project Excel Upload Wizard'

    excel_file = fields.Binary(
        string='Excel File (.xlsx)',
        required=True,
        help='Upload Excel file with Project data. Expected columns: Project Code, Name, Project Manager, Customer, Sales Man, Is Amc, Status, Company, Is AMC Project'
    )
    
    excel_filename = fields.Char(string='Filename')
    
    projects_data_json = fields.Text(
        string='Parsed Projects Data (JSON)',
        help='Temporary storage for parsed Excel data'
    )
    
    error_report_file = fields.Binary(string='Error Report', readonly=True)
    error_report_filename = fields.Char(string='Error Report Filename', readonly=True)

    def action_upload(self):
        """Process Excel upload and create migration lines"""
        self.ensure_one()
        
        if not OPENPYXL_AVAILABLE:
            raise UserError(
                'openpyxl library is required. Please install it:\n'
                'pip install openpyxl\n'
                'Then restart Odoo server.'
            )
        
        if not self.excel_file:
            raise UserError('Please select an Excel file to upload')
        
        try:
            # Decode file
            file_content = base64.b64decode(self.excel_file)
            workbook = load_workbook(io.BytesIO(file_content), data_only=True, read_only=True)
            sheet = workbook.active
            
            # Read header row to find column positions
            headers = []
            header_row = None
            for row_idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
                # Look for header row (first row with text in multiple cells)
                if row and any(cell and str(cell).strip() for cell in row[:9]):  # Check first 9 columns
                    # Check if this looks like a header (contains expected column names)
                    row_values = [str(cell).strip() if cell else '' for cell in row]
                    expected_headers = ['project code', 'name', 'project manager', 'customer', 'sales man', 'is amc', 'status', 'company', 'is amc project']
                    found_headers = sum(1 for val in row_values if val.lower() in [h.lower() for h in expected_headers])
                    
                    if found_headers >= 3:  # Found at least 3 expected headers
                        headers = row_values
                        header_row = row_idx
                        break
            
            if not headers or header_row is None:
                # Assume first row is header
                first_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
                if first_row:
                    headers = [str(cell).strip() if cell else '' for cell in first_row]
                    header_row = 1
                else:
                    raise UserError('Could not find header row in Excel file')
            
            # Find column indices (case-insensitive)
            col_map = {}
            header_lower = [h.lower() for h in headers]
            
            # Map columns
            if 'project code' in header_lower:
                col_map['project_code'] = header_lower.index('project code')
            elif any('project code' in h for h in header_lower):
                col_map['project_code'] = next(i for i, h in enumerate(header_lower) if 'project code' in h)
            
            if 'name' in header_lower:
                col_map['name'] = header_lower.index('name')
            
            if 'project manager' in header_lower:
                col_map['project_manager'] = header_lower.index('project manager')
            elif any('project manager' in h for h in header_lower):
                col_map['project_manager'] = next(i for i, h in enumerate(header_lower) if 'project manager' in h)
            
            if 'customer' in header_lower:
                col_map['customer'] = header_lower.index('customer')
            
            if 'sales man' in header_lower:
                col_map['sales_man'] = header_lower.index('sales man')
            elif any('sales man' in h for h in header_lower):
                col_map['sales_man'] = next(i for i, h in enumerate(header_lower) if 'sales man' in h)
            
            if 'is amc' in header_lower:
                col_map['is_amc'] = header_lower.index('is amc')
            elif any('is amc' in h for h in header_lower):
                col_map['is_amc'] = next(i for i, h in enumerate(header_lower) if 'is amc' in h)
            
            if 'status' in header_lower:
                col_map['status'] = header_lower.index('status')
            
            if 'company' in header_lower:
                col_map['company'] = header_lower.index('company')
            
            if 'is amc project' in header_lower:
                col_map['is_amc_project'] = header_lower.index('is amc project')
            elif any('is amc project' in h for h in header_lower):
                col_map['is_amc_project'] = next(i for i, h in enumerate(header_lower) if 'is amc project' in h)
            
            if 'project_code' not in col_map:
                raise UserError('Could not find "Project Code" column in Excel file. Please ensure the file has a "Project Code" column.')
            
            # Parse data rows
            projects_data = []
            for row_idx, row in enumerate(sheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
                # Skip empty rows
                if not row or not any(cell for cell in row):
                    continue
                
                # Get project code (required)
                project_code_col = col_map.get('project_code')
                if project_code_col is None or project_code_col >= len(row) or not row[project_code_col]:
                    continue
                
                project_code = str(row[project_code_col]).strip()
                if not project_code or project_code.lower() in ['project code', 'project_code', 'code']:
                    continue
                
                # Build project data
                project_data = {
                    'project_code': project_code,
                }
                
                # Get optional fields
                if 'name' in col_map and col_map['name'] < len(row):
                    name_val = row[col_map['name']]
                    if name_val:
                        project_data['name'] = str(name_val).strip()
                
                if 'project_manager' in col_map and col_map['project_manager'] < len(row):
                    pm_val = row[col_map['project_manager']]
                    if pm_val:
                        project_data['project_manager_name'] = str(pm_val).strip()
                
                if 'customer' in col_map and col_map['customer'] < len(row):
                    customer_val = row[col_map['customer']]
                    if customer_val:
                        project_data['customer_name'] = str(customer_val).strip()
                
                if 'sales_man' in col_map and col_map['sales_man'] < len(row):
                    sales_val = row[col_map['sales_man']]
                    if sales_val:
                        project_data['sales_man_name'] = str(sales_val).strip()
                
                if 'is_amc' in col_map and col_map['is_amc'] < len(row):
                    is_amc_val = row[col_map['is_amc']]
                    if is_amc_val:
                        project_data['is_amc'] = str(is_amc_val).strip()
                
                if 'status' in col_map and col_map['status'] < len(row):
                    status_val = row[col_map['status']]
                    if status_val:
                        project_data['status_name'] = str(status_val).strip()
                
                if 'company' in col_map and col_map['company'] < len(row):
                    company_val = row[col_map['company']]
                    if company_val:
                        project_data['company_name'] = str(company_val).strip()
                
                if 'is_amc_project' in col_map and col_map['is_amc_project'] < len(row):
                    is_amc_project_val = row[col_map['is_amc_project']]
                    if is_amc_project_val:
                        project_data['is_amc_project'] = str(is_amc_project_val).strip()
                
                projects_data.append(project_data)
            
            workbook.close()
            
            if not projects_data:
                raise UserError('No project data found in Excel file. Please ensure the file contains project records.')
            
            # Store parsed data for the Proceed button
            self.projects_data_json = json.dumps(projects_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Excel Parsed Successfully',
                    'message': f'Found {len(projects_data)} project(s). Click "Proceed" to import to Project Migration list.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error uploading Excel: %s", str(e), exc_info=True)
            raise UserError('Error uploading Excel file: %s' % str(e))
    
    def action_proceed_import(self):
        """Import projects from parsed Excel data to Migration Lines only (not Projects)"""
        self.ensure_one()
        
        if not self.projects_data_json:
            raise UserError('No parsed data found. Please upload Excel file first.')
        
        try:
            projects_data = json.loads(self.projects_data_json)
        except json.JSONDecodeError as e:
            _logger.error(f"JSON decode error: {str(e)}")
            raise UserError(f'Error parsing stored data: {str(e)}\n\nPlease upload Excel file again.')
        
        if not projects_data:
            raise UserError('No project data found in parsed Excel file.')
        
        _logger.info(f"Starting import of {len(projects_data)} projects to Migration Lines")
        
        MigrationLineModel = self.env['project.migration.line']
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        # Check which migration lines already exist
        project_codes = [p.get('project_code') for p in projects_data if p.get('project_code')]
        if not project_codes:
            raise UserError('No valid project codes found in Excel data.')
        
        existing_migration_lines = MigrationLineModel.search([('project_code', 'in', project_codes)])
        existing_codes = set(existing_migration_lines.mapped('project_code'))
        
        _logger.info(f"Found {len(existing_codes)} existing migration lines out of {len(project_codes)} total")
        
        processed_count = 0
        skip_values = ['project code', 'project_code', 'code', 'draft', 'status', 'customer']
        
        for idx, project_data in enumerate(projects_data, 1):
            project_code = project_data.get('project_code')
            if not project_code:
                _logger.warning(f"Row {idx}: Missing project code, skipping")
                continue
            
            # Skip if project_code looks like a header value
            project_code_str = str(project_code).strip()
            if project_code_str.lower() in skip_values:
                _logger.warning(f"Row {idx}: Project code '{project_code}' appears to be a header, skipping")
                continue
            
            processed_count += 1
            
            try:
                existing_line = MigrationLineModel.search([
                    ('project_code', '=', project_code)
                ], limit=1)
                
                if existing_line:
                    # Update existing migration line
                    existing_line.write({
                        'name': project_data.get('name'),
                        'project_manager_name': project_data.get('project_manager_name'),
                        'customer_name': project_data.get('customer_name'),
                        'sales_man_name': project_data.get('sales_man_name'),
                        'is_amc': project_data.get('is_amc'),
                        'status_name': project_data.get('status_name'),
                        'company_name': project_data.get('company_name'),
                        'is_amc_project': project_data.get('is_amc_project'),
                        'status': 'pending_migration',  # Reset to pending if updating
                        'status_message': 'Updated from Excel upload',
                        'error_message': False,  # Clear any previous errors
                    })
                    updated_count += 1
                    _logger.info(f"Updated migration line for project {project_code}")
                else:
                    # Create new migration line
                    migration_line_vals = {
                        'project_code': project_code,
                        'name': project_data.get('name'),
                        'project_manager_name': project_data.get('project_manager_name'),
                        'customer_name': project_data.get('customer_name'),
                        'sales_man_name': project_data.get('sales_man_name'),
                        'is_amc': project_data.get('is_amc'),
                        'status_name': project_data.get('status_name'),
                        'company_name': project_data.get('company_name'),
                        'is_amc_project': project_data.get('is_amc_project'),
                        'status': 'pending_migration',
                        'status_message': 'Uploaded from Excel - ready for migration',
                    }
                    migration_line = MigrationLineModel.create(migration_line_vals)
                    created_count += 1
                    _logger.info(f"Created migration line for project {project_code}")
                
            except Exception as e:
                error_msg = str(e)
                _logger.error(f"Error creating/updating migration line for {project_code}: {error_msg}", exc_info=True)
                errors.append(f'Project {project_code}: {error_msg}')
                continue
            
            # Commit more frequently to avoid transaction issues
            if idx % 50 == 0:
                try:
                    self.env.cr.commit()
                    _logger.info(f"Progress: Created {created_count}, Updated {updated_count} migration lines (committed at row {idx})")
                except Exception as commit_error:
                    _logger.error(f"Error committing at row {idx}: {commit_error}")
                    self.env.cr.rollback()
                    raise UserError(f'Error committing batch at row {idx}: {commit_error}. Processed {created_count + updated_count} migration lines so far.')
        
        self.env.cr.commit()
        _logger.info(f"Import completed: {processed_count} processed, {created_count} created, {updated_count} updated, {len(errors)} errors")
        
        # If no projects were processed at all, something is wrong
        if processed_count == 0:
            raise UserError('No projects were processed. Please check that the Excel file contains valid project codes.')
        
        # Log detailed summary
        if errors:
            _logger.warning(f"Import errors summary: {len(errors)} errors occurred")
            for error in errors[:10]:  # Log first 10 errors
                _logger.warning(f"  - {error}")
        
        # Prepare summary message
        notification_title = 'Import Successful'
        notification_msg = f'Successfully imported {created_count + updated_count} project(s) to Project Migration list'
        if created_count > 0:
            notification_msg += f'\n  - Created: {created_count} new migration line(s)'
        if updated_count > 0:
            notification_msg += f'\n  - Updated: {updated_count} existing migration line(s)'
        if errors:
            notification_msg += f'\n  - Errors: {len(errors)} error(s) occurred'
        
        # Return action to view migration lines - use the action reference
        try:
            action = self.env.ref('odoo14_to_19_migration.action_project_migration').read()[0]
            if project_codes:
                # Filter to show imported projects
                action['domain'] = [('project_code', 'in', project_codes)]
            action['name'] = f'Project Migration - {created_count + updated_count} Imported'
            action['target'] = 'current'
            
            # Add notification
            action['context'] = {
                'default_status': 'pending_migration',
                'search_default_pending': 1,  # Show pending filter by default
            }
            
            return action
        except Exception as e:
            _logger.error(f"Error getting action reference: {str(e)}", exc_info=True)
            # Fallback: return basic action
            return {
                'type': 'ir.actions.act_window',
                'name': f'Project Migration - {created_count + updated_count} Imported',
                'res_model': 'project.migration.line',
                'view_mode': 'list,form',
                'domain': [('project_code', 'in', project_codes)] if project_codes else [],
                'target': 'current',
            }
    
    def action_download_error_report(self):
        """Download the error report Excel file"""
        self.ensure_one()
        if not self.error_report_file:
            raise UserError('No error report available.')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=error_report_file&filename_field=error_report_filename&download=true',
            'target': 'new',
        }

