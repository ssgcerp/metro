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


class AMCSystemTypeUploadWizard(models.TransientModel):
    """Wizard for uploading Excel file with system type names"""
    _name = 'amc.system.type.upload.wizard'
    _description = 'AMC System Type Excel Upload Wizard'

    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=False,
        help='Optional: Select Odoo 14 connection configuration for later status checking'
    )
    
    excel_file = fields.Binary(
        string='Excel File (.xlsx)',
        required=True,
        help='Upload Excel file with system type names in first column'
    )
    
    excel_filename = fields.Char(string='Filename')

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
            
            # Read all rows with system type names in first column
            rows_data = []
            header_row = None
            
            for row_idx, row in enumerate(sheet.iter_rows(min_row=1, values_only=True), start=1):
                if not row or not any(row):  # Skip empty rows
                    continue
                
                # Check if this is a header row
                first_cell = str(row[0]).strip().lower() if row[0] else ''
                if first_cell in ['name', 'system type', 'system type name', 'system_type']:
                    header_row = row_idx
                    continue
                
                # Extract system type name from first column
                system_type_name = str(row[0]).strip() if row[0] else ''
                
                # Only add rows with system type name
                if system_type_name:
                    rows_data.append({
                        'system_type_name': system_type_name,
                    })
            
            workbook.close()
            
            if not rows_data:
                raise UserError('No system type data found in Excel file. Please ensure the file has system type names in the first column.')
            
            # Create migration lines (batch create)
            MigrationLine = self.env['amc.system.type.migration.line']
            created_count = 0
            skipped_count = 0
            
            # Get all system type names from uploaded data
            system_type_names = [r['system_type_name'] for r in rows_data]
            
            # Check which ones already exist (batch check)
            existing_names = set()
            if system_type_names:
                domain = [('uploaded_system_type_name', 'in', system_type_names)]
                if self.config_id:
                    domain.append(('config_id', '=', self.config_id.id))
                existing_records = MigrationLine.search(domain)
                existing_names = set(existing_records.mapped('uploaded_system_type_name'))
            
            # Create records in batch
            lines_to_create = []
            for row_data in rows_data:
                st_name = row_data['system_type_name']
                if st_name not in existing_names:
                    lines_to_create.append({
                        'uploaded_system_type_name': st_name,
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
                'res_model': 'amc.system.type.migration.line',
                'view_mode': 'list,form',
                'target': 'current',
                'domain': domain,
            }
            
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error uploading Excel: %s", str(e), exc_info=True)
            raise UserError('Error uploading Excel file: %s' % str(e))

