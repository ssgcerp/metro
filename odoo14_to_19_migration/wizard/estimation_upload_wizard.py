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


class EstimationUploadWizard(models.TransientModel):
    """Wizard for uploading Excel file with estimation numbers"""
    _name = 'estimation.upload.wizard'
    _description = 'Estimation Excel Upload Wizard'

    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=False,
        help='Optional: Select Odoo 14 connection configuration for later status checking'
    )
    
    excel_file = fields.Binary(
        string='Excel File (.xlsx)',
        required=True,
        help='Upload Excel file with estimation numbers in first column'
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
            
            # Read all rows with columns: Estimation, Customer, Lead, Engineer, Estimated Delivery, Status, Company
            # Expected column order: A=Estimation, B=Customer, C=Lead, D=Engineer, E=Estimated Delivery, F=Status, G=Company
            rows_data = []
            header_row = None
            
            for row_idx, row in enumerate(sheet.iter_rows(min_row=1, values_only=True), start=1):
                if not row or not any(row):  # Skip empty rows
                    continue
                
                # Check if this is a header row
                first_cell = str(row[0]).strip().lower() if row[0] else ''
                if first_cell in ['estimation', 'estimation number', 'estimation number', 'number']:
                    header_row = row_idx
                    continue
                
                # Extract data from columns
                estimation = str(row[0]).strip() if row[0] else ''
                customer = str(row[1]).strip() if len(row) > 1 and row[1] else ''
                lead = str(row[2]).strip() if len(row) > 2 and row[2] else ''
                engineer = str(row[3]).strip() if len(row) > 3 and row[3] else ''
                estimated_delivery = str(row[4]).strip() if len(row) > 4 and row[4] else ''
                excel_status = str(row[5]).strip() if len(row) > 5 and row[5] else ''
                company = str(row[6]).strip() if len(row) > 6 and row[6] else ''
                
                # Only add rows with estimation number
                if estimation:
                    rows_data.append({
                        'estimation': estimation,
                        'customer': customer,
                        'lead': lead,
                        'engineer': engineer,
                        'estimated_delivery': estimated_delivery,
                        'excel_status': excel_status,
                        'company': company,
                    })
            
            workbook.close()
            
            if not rows_data:
                raise UserError('No estimation data found in Excel file. Please ensure the file has the correct columns: Estimation, Customer, Lead, Engineer, Estimated Delivery, Status, Company')
            
            # Create migration lines (batch create)
            MigrationLine = self.env['estimation.migration.line']
            created_count = 0
            skipped_count = 0
            
            # Get all estimation numbers from uploaded data
            estimation_numbers = [r['estimation'] for r in rows_data]
            
            # Check which ones already exist (batch check)
            existing_numbers = set()
            if estimation_numbers:
                domain = [('uploaded_estimation_number', 'in', estimation_numbers)]
                if self.config_id:
                    domain.append(('config_id', '=', self.config_id.id))
                existing_records = MigrationLine.search(domain)
                existing_numbers = set(existing_records.mapped('uploaded_estimation_number'))
            
            # Create records in batch with all fields
            lines_to_create = []
            for row_data in rows_data:
                est_num = row_data['estimation']
                if est_num not in existing_numbers:
                    lines_to_create.append({
                        'uploaded_estimation_number': est_num,
                        'customer': row_data['customer'],
                        'lead': row_data['lead'],
                        'engineer': row_data['engineer'],
                        'estimated_delivery': row_data['estimated_delivery'],
                        'excel_status': row_data['excel_status'],
                        'company': row_data['company'],
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
                'res_model': 'estimation.migration.line',
                'view_mode': 'list,form',
                'target': 'current',
                'domain': domain,
            }
            
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error uploading Excel: %s", str(e), exc_info=True)
            raise UserError('Error uploading Excel file: %s' % str(e))

