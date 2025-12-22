# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import base64
import io

try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

_logger = logging.getLogger(__name__)


class RFQUploadWizard(models.TransientModel):
    """Wizard for uploading Excel file with RFQ numbers"""
    _name = 'rfq.upload.wizard'
    _description = 'RFQ Excel Upload Wizard'

    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=False,
        help='Optional: Select Odoo 14 connection configuration for later status checking'
    )
    
    excel_file = fields.Binary(
        string='Excel File (.xlsx)',
        required=True,
        help='Upload Excel file with RFQ numbers in first column'
    )
    
    excel_filename = fields.Char(string='Filename')

    def action_upload(self):
        """Process Excel upload and create migration lines with all columns"""
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
            
            # Read all rows with columns:
            # Priority, Order Reference, Vendor, Project, Purchase Representative,
            # Order Deadline, Status, Branch/ID, Created on, Effective Date, Receipt Date
            rows_data = []
            header_row = None
            column_mapping = {}  # Map column names to indices
            
            for row_idx, row in enumerate(sheet.iter_rows(min_row=1, values_only=True), start=1):
                if not row or not any(row):  # Skip empty rows
                    continue
                
                # Check if this is a header row
                first_cell = str(row[0]).strip().lower() if row[0] else ''
                if first_cell in ['priority', 'order reference', 'order ref', 'rfq', 'rfq number', 'purchase order']:
                    # This is the header row - map column names to indices
                    header_row = row_idx
                    for col_idx, cell_value in enumerate(row):
                        if cell_value:
                            cell_str = str(cell_value).strip().lower()
                            # Map common column name variations
                            if 'priority' in cell_str:
                                column_mapping['priority'] = col_idx
                            elif 'order reference' in cell_str or 'order ref' in cell_str or 'rfq' in cell_str:
                                column_mapping['order_reference'] = col_idx
                            elif 'vendor' in cell_str or 'supplier' in cell_str:
                                column_mapping['vendor'] = col_idx
                            elif 'project' in cell_str:
                                column_mapping['project'] = col_idx
                            elif 'purchase representative' in cell_str or 'purchaser' in cell_str or 'rep' in cell_str:
                                column_mapping['purchase_representative'] = col_idx
                            elif 'order deadline' in cell_str or 'deadline' in cell_str:
                                column_mapping['order_deadline'] = col_idx
                            elif 'status' in cell_str:
                                column_mapping['status'] = col_idx
                            elif 'branch' in cell_str or 'company' in cell_str:
                                column_mapping['branch'] = col_idx
                            elif 'created on' in cell_str or 'created' in cell_str:
                                column_mapping['created_on'] = col_idx
                            elif 'effective date' in cell_str or 'effective' in cell_str:
                                column_mapping['effective_date'] = col_idx
                            elif 'receipt date' in cell_str or 'receipt' in cell_str:
                                column_mapping['receipt_date'] = col_idx
                    continue
                
                # Extract data from columns using mapping
                rfq_number = ''
                if 'order_reference' in column_mapping:
                    rfq_number = str(row[column_mapping['order_reference']]).strip() if len(row) > column_mapping['order_reference'] and row[column_mapping['order_reference']] else ''
                else:
                    # Fallback: try first column if no mapping found
                    rfq_number = str(row[0]).strip() if row[0] else ''
                
                # Only process rows with RFQ number
                if not rfq_number:
                    continue
                
                # Extract other fields
                priority = ''
                if 'priority' in column_mapping and len(row) > column_mapping['priority']:
                    priority = str(row[column_mapping['priority']]).strip() if row[column_mapping['priority']] else ''
                
                vendor = ''
                if 'vendor' in column_mapping and len(row) > column_mapping['vendor']:
                    vendor = str(row[column_mapping['vendor']]).strip() if row[column_mapping['vendor']] else ''
                
                project = ''
                if 'project' in column_mapping and len(row) > column_mapping['project']:
                    project = str(row[column_mapping['project']]).strip() if row[column_mapping['project']] else ''
                
                purchase_representative = ''
                if 'purchase_representative' in column_mapping and len(row) > column_mapping['purchase_representative']:
                    purchase_representative = str(row[column_mapping['purchase_representative']]).strip() if row[column_mapping['purchase_representative']] else ''
                
                order_deadline = ''
                if 'order_deadline' in column_mapping and len(row) > column_mapping['order_deadline']:
                    order_deadline = str(row[column_mapping['order_deadline']]).strip() if row[column_mapping['order_deadline']] else ''
                
                excel_status = ''
                if 'status' in column_mapping and len(row) > column_mapping['status']:
                    excel_status = str(row[column_mapping['status']]).strip() if row[column_mapping['status']] else ''
                
                branch = ''
                if 'branch' in column_mapping and len(row) > column_mapping['branch']:
                    branch = str(row[column_mapping['branch']]).strip() if row[column_mapping['branch']] else ''
                
                created_on = ''
                if 'created_on' in column_mapping and len(row) > column_mapping['created_on']:
                    created_on = str(row[column_mapping['created_on']]).strip() if row[column_mapping['created_on']] else ''
                
                effective_date = ''
                if 'effective_date' in column_mapping and len(row) > column_mapping['effective_date']:
                    effective_date = str(row[column_mapping['effective_date']]).strip() if row[column_mapping['effective_date']] else ''
                
                receipt_date = ''
                if 'receipt_date' in column_mapping and len(row) > column_mapping['receipt_date']:
                    receipt_date = str(row[column_mapping['receipt_date']]).strip() if row[column_mapping['receipt_date']] else ''
                
                rows_data.append({
                    'rfq_number': rfq_number,
                    'priority': priority,
                    'vendor': vendor,
                    'project': project,
                    'purchase_representative': purchase_representative,
                    'order_deadline': order_deadline,
                    'excel_status': excel_status,
                    'branch': branch,
                    'created_on': created_on,
                    'effective_date': effective_date,
                    'receipt_date': receipt_date,
                })
            
            workbook.close()
            
            if not rows_data:
                raise UserError('No RFQ data found in Excel file. Please ensure the file has the correct columns: Priority, Order Reference, Vendor, Project, Purchase Representative, Order Deadline, Status, Branch/ID, Created on, Effective Date, Receipt Date')
            
            # Create migration lines (batch create)
            MigrationLine = self.env['rfq.migration.line']
            created_count = 0
            skipped_count = 0
            
            # Get all RFQ numbers from uploaded data
            rfq_numbers = [r['rfq_number'] for r in rows_data]
            
            # Check which ones already exist (batch check)
            existing_numbers = set()
            if rfq_numbers:
                domain = [('uploaded_rfq_number', 'in', rfq_numbers)]
                if self.config_id:
                    domain.append(('config_id', '=', self.config_id.id))
                existing_records = MigrationLine.search(domain)
                existing_numbers = set(existing_records.mapped('uploaded_rfq_number'))
            
            # Create records in batch with all fields
            lines_to_create = []
            for row_data in rows_data:
                rfq_num = row_data['rfq_number']
                if rfq_num not in existing_numbers:
                    lines_to_create.append({
                        'uploaded_rfq_number': rfq_num,
                        'vendor': row_data.get('vendor', ''),
                        'project': row_data.get('project', ''),
                        'excel_status': row_data.get('excel_status', ''),
                        'company': row_data.get('branch', ''),  # Use branch as company
                        'priority': row_data.get('priority', ''),
                        'purchase_representative': row_data.get('purchase_representative', ''),
                        'order_deadline': row_data.get('order_deadline', ''),
                        'created_on': row_data.get('created_on', ''),
                        'effective_date': row_data.get('effective_date', ''),
                        'receipt_date': row_data.get('receipt_date', ''),
                        'config_id': self.config_id.id if self.config_id else False,
                        'status': 'pending_migration',
                        'status_message': 'Uploaded from Excel',
                    })
                    created_count += 1
                else:
                    skipped_count += 1
            
            # Batch create all records
            if lines_to_create:
                MigrationLine.create(lines_to_create)
                self.env.cr.commit()  # Commit after creation
            
            # Return to list view to show uploaded lines
            domain = []
            if self.config_id:
                domain = [('config_id', '=', self.config_id.id)]
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'rfq.migration.line',
                'view_mode': 'list,form',
                'target': 'current',
                'domain': domain,
            }
            
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error uploading Excel: %s", str(e), exc_info=True)
            raise UserError('Error uploading Excel file: %s' % str(e))

