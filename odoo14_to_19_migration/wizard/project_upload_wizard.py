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
                    'message': f'Found {len(projects_data)} project(s). Click "Proceed" to import directly to Projects.',
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
        """Import projects from parsed Excel data to both Migration Lines and Projects"""
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
        
        _logger.info(f"Starting import of {len(projects_data)} projects to both Migration Lines and Projects")
        
        ProjectModel = self.env['project.project']
        MigrationLineModel = self.env['project.migration.line']
        created_count = 0
        skipped_count = 0
        errors = []
        error_details_list = []
        created_project_ids = []
        created_migration_line_ids = []
        
        # Check which projects already exist in both models
        project_codes = [p.get('project_code') for p in projects_data if p.get('project_code')]
        if not project_codes:
            raise UserError('No valid project codes found in Excel data.')
        
        existing_projects = ProjectModel.search([('project_code', 'in', project_codes)])
        existing_codes = set(existing_projects.mapped('project_code'))
        
        existing_migration_lines = MigrationLineModel.search([('project_code', 'in', project_codes)])
        existing_migration_codes = set(existing_migration_lines.mapped('project_code'))
        
        _logger.info(f"Found {len(existing_codes)} existing projects and {len(existing_migration_codes)} existing migration lines out of {len(project_codes)} total")
        
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
            
            # Prepare data for migration line (always create/update this)
            customer_name = project_data.get('customer_name')
            status_name = project_data.get('status_name')
            project_exists = project_code in existing_codes
            
            # Try to create/update project if it doesn't exist
            project = None
            project_error = None
            
            # Use savepoint to handle transaction errors
            savepoint_name = f'project_import_{idx}'
            savepoint_created = False
            try:
                # Check if transaction is already aborted
                try:
                    self.env.cr.execute('SELECT 1')
                except Exception:
                    # Transaction is aborted, rollback everything
                    _logger.error(f"Transaction aborted before processing project {project_code}, rolling back all changes")
                    self.env.cr.rollback()
                    raise UserError('Transaction was aborted due to previous errors. Please try again with a smaller batch or fix the errors in your Excel file.')
                
                self.env.cr.execute(f'SAVEPOINT {savepoint_name}')
                savepoint_created = True
                
                if project_exists:
                    # Project already exists, use cached result
                    project = None
                    for existing_project in existing_projects:
                        if existing_project.project_code == project_code:
                            project = existing_project
                            break
                    if not project:
                        _logger.warning(f"Project {project_code} marked as existing but not found in cache")
                    skipped_count += 1
                    _logger.info(f"Project {project_code} already exists in Projects")
                else:
                    # Try to create the project
                    try:
                        # Find customer by name
                        customer = False
                        if customer_name:
                            customer = self.env['res.partner'].search([
                                ('name', '=', customer_name)
                            ], limit=1)
                            
                            if not customer:
                                customer = self.env['res.partner'].search([
                                    ('name', 'ilike', customer_name)
                                ], limit=1)
                            
                            if not customer:
                                project_error = f'Customer "{customer_name}" not found'
                                _logger.warning(f"Customer not found: {customer_name} for project {project_code}")
                        else:
                            project_error = 'Customer name is required'
                            _logger.warning(f"Customer name missing for project {project_code}")
                        
                        if not project_error:
                            # Find company by name
                            company = False
                            company_name = project_data.get('company_name')
                            if company_name:
                                company = self.env['res.company'].search([
                                    ('name', 'ilike', company_name)
                                ], limit=1)
                            
                            if not company:
                                company = self.env.company
                            
                            # Find project manager (from Employees/Users)
                            project_manager = False
                            project_manager_name = project_data.get('project_manager_name')
                            if project_manager_name:
                                # Try to find by employee name
                                employee = self.env['hr.employee'].search([
                                    ('name', '=', project_manager_name)
                                ], limit=1)
                                
                                if not employee:
                                    employee = self.env['hr.employee'].search([
                                        ('name', 'ilike', project_manager_name)
                                    ], limit=1)
                                
                                if employee and employee.user_id:
                                    project_manager = employee.user_id
                                else:
                                    # Try to find by user name
                                    project_manager = self.env['res.users'].search([
                                        ('name', '=', project_manager_name)
                                    ], limit=1)
                                    
                                    if not project_manager:
                                        project_manager = self.env['res.users'].search([
                                            ('name', 'ilike', project_manager_name)
                                        ], limit=1)
                            
                            # Find sales man (from Employees/Users)
                            sales_man = False
                            sales_man_name = project_data.get('sales_man_name')
                            if sales_man_name:
                                # Try to find by employee name
                                employee = self.env['hr.employee'].search([
                                    ('name', '=', sales_man_name)
                                ], limit=1)
                                
                                if not employee:
                                    employee = self.env['hr.employee'].search([
                                        ('name', 'ilike', sales_man_name)
                                    ], limit=1)
                                
                                if employee and employee.user_id:
                                    sales_man = employee.user_id
                                else:
                                    # Try to find by user name
                                    sales_man = self.env['res.users'].search([
                                        ('name', '=', sales_man_name)
                                    ], limit=1)
                                    
                                    if not sales_man:
                                        sales_man = self.env['res.users'].search([
                                            ('name', 'ilike', sales_man_name)
                                        ], limit=1)
                            
                            # Find stage by status name
                            stage = False
                            if status_name:
                                stage = self.env['fc.project.stage'].search([
                                    ('name', '=', status_name)
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
                            is_amc_val = project_data.get('is_amc')
                            if is_amc_val:
                                is_amc_str = str(is_amc_val).strip().lower()
                                is_amc = is_amc_str in ('true', 'yes', '1', 'y')
                            
                            is_amc_project = False
                            is_amc_project_val = project_data.get('is_amc_project')
                            if is_amc_project_val:
                                is_amc_project_str = str(is_amc_project_val).strip().lower()
                                is_amc_project = is_amc_project_str in ('true', 'yes', '1', 'y')
                            
                            # Prepare project values
                            project_vals = {
                                'name': project_data.get('name') or project_code,
                                'project_code': project_code,
                                'partner_id': customer.id if customer else False,
                                'company_id': company.id,
                                'user_id': project_manager.id if project_manager else False,
                                'stage_id': stage.id if stage else False,
                                'is_amc': is_amc,
                                'is_amc_project': is_amc_project,
                            }
                            
                            # Create Project
                            project = ProjectModel.create(project_vals)
                            created_project_ids.append(project.id)
                            created_count += 1
                            _logger.info(f"Created project {project_code}")
                    
                    except Exception as e:
                        project_error = str(e)
                        _logger.error(f"Error creating project {project_code}: {project_error}", exc_info=True)
                        # Rollback to savepoint on error
                        if savepoint_created:
                            try:
                                self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                            except Exception as rollback_error:
                                _logger.error(f"Error rolling back to savepoint: {rollback_error}")
                                self.env.cr.rollback()
                                raise UserError(f'Transaction error for project {project_code}: {rollback_error}. Please try again.')
                
                # Always create/update Migration Line
                try:
                    existing_line = MigrationLineModel.search([
                        ('project_code', '=', project_code)
                    ], limit=1)
                    
                    if existing_line:
                        # Update existing migration line
                        update_vals = {
                            'name': project_data.get('name'),
                            'project_manager_name': project_data.get('project_manager_name'),
                            'customer_name': customer_name,
                            'sales_man_name': project_data.get('sales_man_name'),
                            'is_amc': project_data.get('is_amc'),
                            'status_name': status_name,
                            'company_name': project_data.get('company_name'),
                            'is_amc_project': project_data.get('is_amc_project'),
                        }
                        if project:
                            update_vals.update({
                                'status': 'migrated',
                                'status_message': 'Imported directly from Excel via Upload Wizard',
                                'odoo19_project_id': project.id,
                                'migration_date': fields.Datetime.now(),
                            })
                        elif project_error:
                            update_vals.update({
                                'status': 'error',
                                'status_message': f'Project creation failed: {project_error}',
                                'error_message': project_error,
                            })
                        existing_line.write(update_vals)
                        _logger.info(f"Updated migration line for project {project_code}")
                    else:
                        # Create new migration line
                        migration_line_vals = {
                            'project_code': project_code,
                            'name': project_data.get('name'),
                            'project_manager_name': project_data.get('project_manager_name'),
                            'customer_name': customer_name,
                            'sales_man_name': project_data.get('sales_man_name'),
                            'is_amc': project_data.get('is_amc'),
                            'status_name': status_name,
                            'company_name': project_data.get('company_name'),
                            'is_amc_project': project_data.get('is_amc_project'),
                        }
                        if project:
                            migration_line_vals.update({
                                'status': 'migrated',
                                'status_message': 'Imported directly from Excel via Upload Wizard',
                                'odoo19_project_id': project.id,
                                'migration_date': fields.Datetime.now(),
                            })
                        elif project_error:
                            migration_line_vals.update({
                                'status': 'error',
                                'status_message': f'Project creation failed: {project_error}',
                                'error_message': project_error,
                            })
                        else:
                            migration_line_vals.update({
                                'status': 'pending_migration',
                                'status_message': 'Awaiting project creation',
                            })
                        migration_line = MigrationLineModel.create(migration_line_vals)
                        created_migration_line_ids.append(migration_line.id)
                        _logger.info(f"Created migration line for project {project_code}")
                
                except Exception as e:
                    _logger.error(f"Error creating/updating migration line for {project_code}: {str(e)}", exc_info=True)
                    if project_error:
                        errors.append(f'Project {project_code}: {project_error} (Migration line also failed: {str(e)})')
                    else:
                        errors.append(f'Project {project_code}: Migration line failed: {str(e)}')
                    # Rollback to savepoint on error
                    if savepoint_created:
                        try:
                            self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                        except Exception as rollback_error:
                            _logger.error(f"Error rolling back to savepoint: {rollback_error}")
                            self.env.cr.rollback()
                            raise UserError(f'Transaction error for project {project_code} migration line: {rollback_error}. Please try again.')
                    continue
                
                # Release savepoint on success
                if savepoint_created:
                    try:
                        self.env.cr.execute(f'RELEASE SAVEPOINT {savepoint_name}')
                    except Exception as release_error:
                        _logger.error(f"Error releasing savepoint: {release_error}")
                        self.env.cr.rollback()
                        raise UserError(f'Transaction error releasing savepoint for project {project_code}: {release_error}. Please try again.')
                
            except Exception as e:
                # Outer exception handler for savepoint errors
                _logger.error(f"Error in savepoint block for {project_code}: {str(e)}", exc_info=True)
                if savepoint_created:
                    try:
                        self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                    except Exception as rollback_error:
                        _logger.error(f"Error rolling back to savepoint in outer handler: {rollback_error}")
                        self.env.cr.rollback()
                        raise UserError(f'Transaction corrupted after error with project {project_code}. All changes rolled back. Please try again.')
                errors.append(f'Project {project_code}: {str(e)}')
                continue
            
            # Track errors with details
            if project_error and not project_exists:
                error_msg = f'Project {project_code}: {project_error}'
                errors.append(error_msg)
                error_details_list.append({
                    'project': project_code,
                    'customer': customer_name or 'N/A',
                })
            
            # Commit more frequently to avoid transaction issues
            if idx % 50 == 0:
                try:
                    self.env.cr.commit()
                    _logger.info(f"Progress: Created {created_count}/{len(projects_data)} projects and {len(created_migration_line_ids)} migration lines (committed at row {idx})")
                except Exception as commit_error:
                    _logger.error(f"Error committing at row {idx}: {commit_error}")
                    self.env.cr.rollback()
                    raise UserError(f'Error committing batch at row {idx}: {commit_error}. Processed {created_count} projects so far.')
        
        self.env.cr.commit()
        _logger.info(f"Import completed: {processed_count} processed, {created_count} projects created, {len(created_migration_line_ids)} migration lines created, {skipped_count} skipped, {len(errors)} errors")
        
        # If no projects were processed at all, something is wrong
        if processed_count == 0:
            raise UserError('No projects were processed. Please check that the Excel file contains valid project codes.')
        
        # Log detailed summary
        if errors:
            _logger.warning(f"Import errors summary: {len(errors)} errors occurred")
            for error in errors[:10]:  # Log first 10 errors
                _logger.warning(f"  - {error}")
        
        # Generate error report Excel file if there are errors
        error_report_data = None
        error_report_filename = None
        if error_details_list and OPENPYXL_AVAILABLE and Workbook:
            try:
                wb = Workbook()
                ws = wb.active
                ws.title = "Error Report"
                
                # Write headers
                ws['A1'] = 'Project Code'
                ws['B1'] = 'Customer'
                
                # Make headers bold
                from openpyxl.styles import Font
                header_font = Font(bold=True)
                ws['A1'].font = header_font
                ws['B1'].font = header_font
                
                # Write error data
                for idx, error_detail in enumerate(error_details_list, start=2):
                    ws[f'A{idx}'] = error_detail['project']
                    ws[f'B{idx}'] = error_detail['customer']
                
                # Auto-adjust column widths
                ws.column_dimensions['A'].width = 30
                ws.column_dimensions['B'].width = 50
                
                # Save to BytesIO
                output = io.BytesIO()
                wb.save(output)
                output.seek(0)
                
                error_report_data = base64.b64encode(output.getvalue())
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                error_report_filename = f'Project_Import_Errors_{timestamp}.xlsx'
                
                # Store in wizard record
                self.error_report_file = error_report_data
                self.error_report_filename = error_report_filename
                
                _logger.info(f"Generated error report with {len(error_details_list)} errors")
            except Exception as e:
                _logger.error(f"Error generating error report: {str(e)}", exc_info=True)
        
        # Prepare summary message
        if created_count > 0:
            notification_title = 'Import Successful'
            notification_msg = f'Successfully created {created_count} project(s) in Projects'
            if len(created_migration_line_ids) > 0:
                notification_msg += f' and {len(created_migration_line_ids)} migration line(s) in Project Migration'
            if skipped_count > 0:
                notification_msg += f'\nSkipped {skipped_count} project(s) (already exist)'
            if errors:
                notification_msg += f'\n{len(errors)} error(s) occurred'
            notification_type = 'success' if not errors else 'warning'
        else:
            notification_title = 'Import Failed'
            notification_msg = f'No projects were created. '
            if skipped_count > 0:
                notification_msg += f'{skipped_count} already exist. '
            if errors:
                notification_msg += f'{len(errors)} error(s) occurred.'
                error_preview = '\n'.join(errors[:5])
                if len(errors) > 5:
                    error_preview += f'\n... and {len(errors) - 5} more (check server logs)'
                notification_msg += f'\n\nErrors:\n{error_preview}'
            else:
                notification_msg += 'Please check the data.'
            notification_type = 'danger'
        
        # Return action to view projects or show errors with download option
        if created_count > 0:
            # Success - show created projects
            action = {
                'type': 'ir.actions.act_window',
                'name': f'Projects - {created_count} Imported',
                'res_model': 'project.project',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_project_ids)],
                'target': 'current',
            }
            if error_details_list and error_report_filename:
                action['context'] = {
                    'error_report_available': True,
                    'error_report_filename': error_report_filename,
                }
            return action
        else:
            # No projects created - show error notification with download option
            if errors:
                error_preview = '\n'.join(errors[:10])
                if len(errors) > 10:
                    error_preview += f'\n... and {len(errors) - 10} more errors'
                full_message = f'{notification_msg}\n\nError Details:\n{error_preview}'
                
                if error_report_filename:
                    full_message += f'\n\nError report Excel file has been generated and is available for download.'
            else:
                full_message = notification_msg
            
            # Return wizard form with error report download button
            if error_report_filename:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Import Completed - Errors Found',
                    'res_model': 'project.upload.wizard',
                    'view_mode': 'form',
                    'res_id': self.id,
                    'target': 'new',
                    'context': {'error_report_available': True},
                }
            else:
                raise UserError(f'{notification_title}\n\n{full_message}')
    
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

