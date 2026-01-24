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


class AMCContractUploadWizard(models.TransientModel):
    """Wizard for uploading Excel file with AMC contract data"""
    _name = 'amc.contract.upload.wizard'
    _description = 'AMC Contract Excel Upload Wizard'

    excel_file = fields.Binary(
        string='Excel File (.xlsx)',
        required=True,
        help='Upload Excel file with AMC contract data. Expected columns: Contract, Start Date, End Date, Customer, Contract Value, Status, Contract Date, Company'
    )
    
    excel_filename = fields.Char(string='Filename')
    
    contracts_data_json = fields.Text(
        string='Parsed Contracts Data (JSON)',
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
                if row and any(cell and str(cell).strip() for cell in row[:7]):  # Check first 7 columns
                    # Check if this looks like a header (contains expected column names)
                    row_values = [str(cell).strip() if cell else '' for cell in row]
                    expected_headers = ['contract', 'start date', 'end date', 'customer', 'contract value', 'status', 'contract date', 'company', 'branch/id', 'branch', 'branch id']
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
            if 'contract' in header_lower:
                col_map['contract'] = header_lower.index('contract')
            elif any('contract' in h for h in header_lower):
                col_map['contract'] = next(i for i, h in enumerate(header_lower) if 'contract' in h)
            
            if 'start date' in header_lower:
                col_map['start_date'] = header_lower.index('start date')
            elif any('start' in h and 'date' in h for h in header_lower):
                col_map['start_date'] = next(i for i, h in enumerate(header_lower) if 'start' in h and 'date' in h)
            
            if 'end date' in header_lower:
                col_map['end_date'] = header_lower.index('end date')
            elif any('end' in h and 'date' in h for h in header_lower):
                col_map['end_date'] = next(i for i, h in enumerate(header_lower) if 'end' in h and 'date' in h)
            
            if 'customer' in header_lower:
                col_map['customer'] = header_lower.index('customer')
            elif any('customer' in h for h in header_lower):
                col_map['customer'] = next(i for i, h in enumerate(header_lower) if 'customer' in h)
            
            if 'contract value' in header_lower:
                col_map['contract_value'] = header_lower.index('contract value')
            elif any('value' in h for h in header_lower):
                col_map['contract_value'] = next(i for i, h in enumerate(header_lower) if 'value' in h)
            
            if 'status' in header_lower:
                col_map['status'] = header_lower.index('status')
            
            if 'contract date' in header_lower:
                col_map['contract_date'] = header_lower.index('contract date')
            elif any('contract date' in h for h in header_lower):
                col_map['contract_date'] = next(i for i, h in enumerate(header_lower) if 'contract date' in h)
            
            # Map Company column (case-insensitive)
            if 'company' in header_lower:
                col_map['company'] = header_lower.index('company')
            
            # Map Branch/ID column (case-insensitive, accepts "Branch/ID", "Branch ID", "Branch")
            if 'branch/id' in header_lower:
                col_map['branch_id'] = header_lower.index('branch/id')
            elif 'branch id' in header_lower:
                col_map['branch_id'] = header_lower.index('branch id')
            elif 'branch' in header_lower and 'company' not in header_lower:
                # Only use 'branch' if 'company' is not present
                col_map['branch_id'] = header_lower.index('branch')
            
            if 'contract' not in col_map:
                raise UserError('Could not find "Contract" column in Excel file. Please ensure the file has a "Contract" column.')
            
            # Parse data rows
            contracts_data = []
            for row_idx, row in enumerate(sheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
                # Skip empty rows
                if not row or not any(cell for cell in row):
                    continue
                
                # Get contract number (required)
                contract_col = col_map.get('contract')
                if contract_col is None or contract_col >= len(row) or not row[contract_col]:
                    continue
                
                contract_number = str(row[contract_col]).strip()
                if not contract_number or contract_number.lower() in ['contract', 'contract number']:
                    continue
                
                # Build contract data
                contract_data = {
                    'contract_number': contract_number,
                }
                
                # Get optional fields
                if 'start_date' in col_map and col_map['start_date'] < len(row):
                    start_date_val = row[col_map['start_date']]
                    if start_date_val:
                        try:
                            # Handle date values (can be datetime or string)
                            if isinstance(start_date_val, str):
                                from datetime import datetime
                                contract_data['start_date'] = datetime.strptime(start_date_val.split()[0], '%Y-%m-%d').date()
                            else:
                                contract_data['start_date'] = start_date_val.date() if hasattr(start_date_val, 'date') else start_date_val
                        except:
                            pass
                
                if 'end_date' in col_map and col_map['end_date'] < len(row):
                    end_date_val = row[col_map['end_date']]
                    if end_date_val:
                        try:
                            if isinstance(end_date_val, str):
                                from datetime import datetime
                                contract_data['end_date'] = datetime.strptime(end_date_val.split()[0], '%Y-%m-%d').date()
                            else:
                                contract_data['end_date'] = end_date_val.date() if hasattr(end_date_val, 'date') else end_date_val
                        except:
                            pass
                
                if 'customer' in col_map and col_map['customer'] < len(row):
                    customer_val = row[col_map['customer']]
                    if customer_val:
                        contract_data['customer_name'] = str(customer_val).strip()
                
                if 'contract_value' in col_map and col_map['contract_value'] < len(row):
                    value_val = row[col_map['contract_value']]
                    if value_val:
                        try:
                            # Handle comma-separated numbers
                            if isinstance(value_val, str):
                                value_str = value_val.replace(',', '').strip()
                                contract_data['contract_value'] = float(value_str)
                            else:
                                contract_data['contract_value'] = float(value_val)
                        except:
                            pass
                
                if 'status' in col_map and col_map['status'] < len(row):
                    status_val = row[col_map['status']]
                    if status_val:
                        contract_data['status_name'] = str(status_val).strip()
                
                if 'contract_date' in col_map and col_map['contract_date'] < len(row):
                    contract_date_val = row[col_map['contract_date']]
                    if contract_date_val:
                        try:
                            if isinstance(contract_date_val, str):
                                from datetime import datetime
                                contract_data['contract_date'] = datetime.strptime(contract_date_val.split()[0], '%Y-%m-%d').date()
                            else:
                                contract_data['contract_date'] = contract_date_val.date() if hasattr(contract_date_val, 'date') else contract_date_val
                        except:
                            pass
                
                if 'company' in col_map and col_map['company'] < len(row):
                    company_val = row[col_map['company']]
                    if company_val:
                        contract_data['company_name'] = str(company_val).strip()
                
                if 'branch_id' in col_map and col_map['branch_id'] < len(row):
                    branch_id_val = row[col_map['branch_id']]
                    if branch_id_val:
                        try:
                            # Handle integer or string values
                            if isinstance(branch_id_val, str):
                                branch_id_str = branch_id_val.strip()
                                # Remove any non-numeric characters except minus sign
                                branch_id_str = ''.join(c for c in branch_id_str if c.isdigit() or c == '-')
                                if branch_id_str:
                                    contract_data['odoo14_branch_id'] = int(branch_id_str)
                            else:
                                contract_data['odoo14_branch_id'] = int(branch_id_val)
                        except (ValueError, TypeError):
                            pass
                
                contracts_data.append(contract_data)
            
            workbook.close()
            
            if not contracts_data:
                raise UserError('No contract data found in Excel file. Please ensure the file contains contract records.')
            
            # Store parsed data for the Proceed button
            # Convert dates to strings for JSON serialization
            for contract_data in contracts_data:
                for key in ['start_date', 'end_date', 'contract_date']:
                    if key in contract_data and contract_data[key]:
                        contract_data[key] = str(contract_data[key])
            
            self.contracts_data_json = json.dumps(contracts_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Excel Parsed Successfully',
                    'message': f'Found {len(contracts_data)} contract(s). Click "Proceed" to import directly to AMC Contracts.',
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
        """Import contracts from parsed Excel data to both Migration Lines and AMC Contracts"""
        self.ensure_one()
        
        if not self.contracts_data_json:
            raise UserError('No parsed data found. Please upload Excel file first.')
        
        try:
            contracts_data = json.loads(self.contracts_data_json)
        except json.JSONDecodeError as e:
            _logger.error(f"JSON decode error: {str(e)}")
            raise UserError(f'Error parsing stored data: {str(e)}\n\nPlease upload Excel file again.')
        
        if not contracts_data:
            raise UserError('No contract data found in parsed Excel file.')
        
        _logger.info(f"Starting import of {len(contracts_data)} contracts to both Migration Lines and AMC Contracts")
        
        # Convert date strings back to date objects
        for contract_data in contracts_data:
            for key in ['start_date', 'end_date', 'contract_date']:
                if key in contract_data and contract_data[key]:
                    try:
                        if isinstance(contract_data[key], str):
                            contract_data[key] = fields.Date.from_string(contract_data[key])
                        # If it's already a date object, keep it
                    except:
                        contract_data[key] = None
        
        ContractModel = self.env['amc.contract']
        MigrationLineModel = self.env['amc.contract.migration.line']
        created_count = 0
        skipped_count = 0
        errors = []
        error_details_list = []  # List of dicts with 'contract' and 'customer' keys for Excel report
        created_contract_ids = []
        created_migration_line_ids = []
        
        # Check which contracts already exist in both models
        contract_numbers = [c.get('contract_number') for c in contracts_data if c.get('contract_number')]
        if not contract_numbers:
            raise UserError('No valid contract numbers found in Excel data.')
        
        existing_contracts = ContractModel.search([('name', 'in', contract_numbers)])
        existing_numbers = set(existing_contracts.mapped('name'))
        
        existing_migration_lines = MigrationLineModel.search([('contract_number', 'in', contract_numbers)])
        existing_migration_numbers = set(existing_migration_lines.mapped('contract_number'))
        
        _logger.info(f"Found {len(existing_numbers)} existing contracts and {len(existing_migration_numbers)} existing migration lines out of {len(contract_numbers)} total")
        
        processed_count = 0
        # Common header values to skip
        skip_values = ['contract', 'contract number', 'draft', 'status', 'customer', 'start date', 'end date']
        
        for idx, contract_data in enumerate(contracts_data, 1):
            contract_number = contract_data.get('contract_number')
            if not contract_number:
                _logger.warning(f"Row {idx}: Missing contract number, skipping")
                continue
            
            # Skip if contract_number looks like a header value
            contract_number_str = str(contract_number).strip()
            if contract_number_str.lower() in skip_values:
                _logger.warning(f"Row {idx}: Contract number '{contract_number}' appears to be a header, skipping")
                continue
            
            processed_count += 1
            
            # Prepare data for migration line (always create/update this)
            customer_name = contract_data.get('customer_name')
            status_name = contract_data.get('status_name')
            contract_exists = contract_number in existing_numbers
            
            # Try to create/update contract if it doesn't exist
            contract = None
            contract_error = None
            
            # Use savepoint to handle transaction errors
            savepoint_name = f'amc_import_{idx}'
            savepoint_created = False
            try:
                # Check if transaction is already aborted
                try:
                    self.env.cr.execute('SELECT 1')
                except Exception:
                    # Transaction is aborted, rollback everything
                    _logger.error(f"Transaction aborted before processing contract {contract_number}, rolling back all changes")
                    self.env.cr.rollback()
                    raise UserError('Transaction was aborted due to previous errors. Please try again with a smaller batch or fix the errors in your Excel file.')
                
                self.env.cr.execute(f'SAVEPOINT {savepoint_name}')
                savepoint_created = True
                
                if contract_exists:
                    # Contract already exists, use cached result
                    # Find it from the already-fetched existing_contracts
                    contract = None
                    for existing_contract in existing_contracts:
                        if existing_contract.name == contract_number:
                            contract = existing_contract
                            break
                    if not contract:
                        # Should not happen, but fallback
                        _logger.warning(f"Contract {contract_number} marked as existing but not found in cache")
                    skipped_count += 1
                    _logger.info(f"Contract {contract_number} already exists in AMC Contracts")
                else:
                    # Try to create the contract
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
                                contract_error = f'Customer "{customer_name}" not found'
                                _logger.warning(f"Customer not found: {customer_name} for contract {contract_number}")
                        else:
                            contract_error = 'Customer name is required'
                            _logger.warning(f"Customer name missing for contract {contract_number}")
                        
                        if not contract_error:
                            # Find company by name
                            company = False
                            company_name = contract_data.get('company_name')
                            if company_name:
                                company = self.env['res.company'].search([
                                    ('name', 'ilike', company_name)
                                ], limit=1)
                                
                                if not company:
                                    contract_error = f'Company "{company_name}" not found'
                            
                            if not contract_error and not company:
                                # No company_name specified, use default company
                                company = self.env.company
                        
                        if not contract_error:
                            # Find stage by status name
                            stage = False
                            if status_name:
                                stage = self.env['amc.contract.stage'].search([
                                    ('name', '=', status_name)
                                ], limit=1)
                            
                            if not stage:
                                stage = self.env['amc.contract.stage'].search([
                                    ('is_default', '=', True),
                                    ('name', '=', 'Draft')
                                ], limit=1)
                                if not stage:
                                    stage = self.env['amc.contract.stage'].search([], order='sequence', limit=1)
                            
                            if not stage:
                                contract_error = 'No contract stage found'
                        
                        if not contract_error:
                            # Prepare contract values
                            contract_vals = {
                                'name': contract_number,
                                'customer_id': customer.id if customer else False,
                                'start_date': contract_data.get('start_date'),
                                'end_date': contract_data.get('end_date'),
                                'contract_date': contract_data.get('contract_date') or contract_data.get('start_date') or fields.Date.today(),
                                'contract_value': contract_data.get('contract_value', 0.0),
                                'stage_id': stage.id,
                                'branch_id': company.id if company else self.env.company.id,
                            }
                            
                            # Ensure contract_date is not after start_date
                            if contract_vals.get('start_date') and contract_vals.get('contract_date'):
                                if contract_vals['start_date'] < contract_vals['contract_date']:
                                    contract_vals['contract_date'] = contract_vals['start_date']
                            
                            # Create AMC Contract
                            contract = ContractModel.create(contract_vals)
                            created_contract_ids.append(contract.id)
                            created_count += 1
                            _logger.info(f"Created contract {contract_number}")
                    
                    except Exception as e:
                        contract_error = str(e)
                        _logger.error(f"Error creating contract {contract_number}: {contract_error}", exc_info=True)
                        # Rollback to savepoint on error
                        if savepoint_created:
                            try:
                                self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                            except Exception as rollback_error:
                                _logger.error(f"Error rolling back to savepoint: {rollback_error}")
                                # If rollback fails, the transaction is corrupted
                                self.env.cr.rollback()
                                raise UserError(f'Transaction error for contract {contract_number}: {rollback_error}. Please try again.')
                
                # Always create/update Migration Line
                try:
                    existing_line = MigrationLineModel.search([
                        ('contract_number', '=', contract_number)
                    ], limit=1)
                    
                    if existing_line:
                        # Update existing migration line
                        update_vals = {
                            'start_date': contract_data.get('start_date'),
                            'end_date': contract_data.get('end_date'),
                            'customer_name': customer_name,
                            'contract_value': contract_data.get('contract_value', 0.0),
                            'status_name': status_name,
                            'contract_date': contract_data.get('contract_date'),
                            'odoo14_branch_id': contract_data.get('odoo14_branch_id'),
                        }
                        if contract:
                            update_vals.update({
                                'status': 'migrated',
                                'status_message': 'Imported directly from Excel via Upload Wizard',
                                'odoo19_contract_id': contract.id,
                                'migration_date': fields.Datetime.now(),
                            })
                        elif contract_error:
                            update_vals.update({
                                'status': 'error',
                                'status_message': f'Contract creation failed: {contract_error}',
                                'error_message': contract_error,
                            })
                        existing_line.write(update_vals)
                        _logger.info(f"Updated migration line for contract {contract_number}")
                    else:
                        # Create new migration line
                        migration_line_vals = {
                            'contract_number': contract_number,
                            'start_date': contract_data.get('start_date'),
                            'end_date': contract_data.get('end_date'),
                            'customer_name': customer_name,
                            'contract_value': contract_data.get('contract_value', 0.0),
                            'status_name': status_name,
                            'contract_date': contract_data.get('contract_date'),
                            'odoo14_branch_id': contract_data.get('odoo14_branch_id'),
                        }
                        if contract:
                            migration_line_vals.update({
                                'status': 'migrated',
                                'status_message': 'Imported directly from Excel via Upload Wizard',
                                'odoo19_contract_id': contract.id,
                                'migration_date': fields.Datetime.now(),
                            })
                        elif contract_error:
                            migration_line_vals.update({
                                'status': 'error',
                                'status_message': f'Contract creation failed: {contract_error}',
                                'error_message': contract_error,
                            })
                        else:
                            migration_line_vals.update({
                                'status': 'pending_migration',
                                'status_message': 'Awaiting contract creation',
                            })
                        migration_line = MigrationLineModel.create(migration_line_vals)
                        created_migration_line_ids.append(migration_line.id)
                        _logger.info(f"Created migration line for contract {contract_number}")
                
                except Exception as e:
                    _logger.error(f"Error creating/updating migration line for {contract_number}: {str(e)}", exc_info=True)
                    if contract_error:
                        errors.append(f'Contract {contract_number}: {contract_error} (Migration line also failed: {str(e)})')
                    else:
                        errors.append(f'Contract {contract_number}: Migration line failed: {str(e)}')
                    # Rollback to savepoint on error
                    if savepoint_created:
                        try:
                            self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                        except Exception as rollback_error:
                            _logger.error(f"Error rolling back to savepoint: {rollback_error}")
                            # If rollback fails, the transaction is corrupted
                            self.env.cr.rollback()
                            raise UserError(f'Transaction error for contract {contract_number} migration line: {rollback_error}. Please try again.')
                    continue
                
                # Release savepoint on success
                if savepoint_created:
                    try:
                        self.env.cr.execute(f'RELEASE SAVEPOINT {savepoint_name}')
                    except Exception as release_error:
                        _logger.error(f"Error releasing savepoint: {release_error}")
                        # If release fails, transaction might be corrupted
                        self.env.cr.rollback()
                        raise UserError(f'Transaction error releasing savepoint for contract {contract_number}: {release_error}. Please try again.')
                
            except Exception as e:
                # Outer exception handler for savepoint errors
                _logger.error(f"Error in savepoint block for {contract_number}: {str(e)}", exc_info=True)
                if savepoint_created:
                    try:
                        self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
                    except Exception as rollback_error:
                        _logger.error(f"Error rolling back to savepoint in outer handler: {rollback_error}")
                        # If rollback fails, transaction is corrupted - abort everything
                        self.env.cr.rollback()
                        raise UserError(f'Transaction corrupted after error with contract {contract_number}. All changes rolled back. Please try again.')
                errors.append(f'Contract {contract_number}: {str(e)}')
                continue
            
            # Track errors with details
            if contract_error and not contract_exists:
                error_msg = f'Contract {contract_number}: {contract_error}'
                errors.append(error_msg)
                # Store error details for Excel report
                error_details_list.append({
                    'contract': contract_number,
                    'customer': customer_name or 'N/A',
                })
            
            # Commit more frequently to avoid transaction issues
            if idx % 50 == 0:
                try:
                    self.env.cr.commit()
                    _logger.info(f"Progress: Created {created_count}/{len(contracts_data)} contracts and {len(created_migration_line_ids)} migration lines (committed at row {idx})")
                except Exception as commit_error:
                    _logger.error(f"Error committing at row {idx}: {commit_error}")
                    self.env.cr.rollback()
                    raise UserError(f'Error committing batch at row {idx}: {commit_error}. Processed {created_count} contracts so far.')
        
        self.env.cr.commit()
        _logger.info(f"Import completed: {processed_count} processed, {created_count} contracts created, {len(created_migration_line_ids)} migration lines created, {skipped_count} skipped, {len(errors)} errors")
        
        # If no contracts were processed at all, something is wrong
        if processed_count == 0:
            raise UserError('No contracts were processed. Please check that the Excel file contains valid contract numbers.')
        
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
                ws['A1'] = 'Contract'
                ws['B1'] = 'Customer'
                
                # Make headers bold
                from openpyxl.styles import Font
                header_font = Font(bold=True)
                ws['A1'].font = header_font
                ws['B1'].font = header_font
                
                # Write error data
                for idx, error_detail in enumerate(error_details_list, start=2):
                    ws[f'A{idx}'] = error_detail['contract']
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
                error_report_filename = f'AMC_Contract_Import_Errors_{timestamp}.xlsx'
                
                # Store in wizard record
                self.error_report_file = error_report_data
                self.error_report_filename = error_report_filename
                
                _logger.info(f"Generated error report with {len(error_details_list)} errors")
            except Exception as e:
                _logger.error(f"Error generating error report: {str(e)}", exc_info=True)
                # Don't fail the import if report generation fails
        
        # Prepare summary message
        if created_count > 0:
            notification_title = 'Import Successful'
            notification_msg = f'Successfully created {created_count} contract(s) in AMC Contracts'
            if len(created_migration_line_ids) > 0:
                notification_msg += f' and {len(created_migration_line_ids)} migration line(s) in AMC Contract Migration'
            if skipped_count > 0:
                notification_msg += f'\nSkipped {skipped_count} contract(s) (already exist)'
            if errors:
                notification_msg += f'\n{len(errors)} error(s) occurred'
            notification_type = 'success' if not errors else 'warning'
        else:
            notification_title = 'Import Failed'
            notification_msg = f'No contracts were created. '
            if skipped_count > 0:
                notification_msg += f'{skipped_count} already exist. '
            if errors:
                notification_msg += f'{len(errors)} error(s) occurred.'
                # Show first few errors
                error_preview = '\n'.join(errors[:5])
                if len(errors) > 5:
                    error_preview += f'\n... and {len(errors) - 5} more (check server logs)'
                notification_msg += f'\n\nErrors:\n{error_preview}'
            else:
                notification_msg += 'Please check the data.'
            notification_type = 'danger'
        
        # Return action to view contracts or show errors with download option
        if created_count > 0:
            # Success - show created contracts
            action = {
                'type': 'ir.actions.act_window',
                'name': f'AMC Contracts - {created_count} Imported',
                'res_model': 'amc.contract',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_contract_ids)],
                'target': 'current',
            }
            # If there are errors, include a note about the error report
            if error_details_list and error_report_filename:
                action['context'] = {
                    'error_report_available': True,
                    'error_report_filename': error_report_filename,
                }
            return action
        else:
            # No contracts created - show error notification with download option
            if errors:
                # Show first 10 errors in the message
                error_preview = '\n'.join(errors[:10])
                if len(errors) > 10:
                    error_preview += f'\n... and {len(errors) - 10} more errors'
                full_message = f'{notification_msg}\n\nError Details:\n{error_preview}'
                
                # If error report was generated, add download message
                if error_report_filename:
                    full_message += f'\n\nError report Excel file has been generated and is available for download.'
            else:
                full_message = notification_msg
            
            # Return wizard form with error report download button
            if error_report_filename:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Import Completed - Errors Found',
                    'res_model': 'amc.contract.upload.wizard',
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
