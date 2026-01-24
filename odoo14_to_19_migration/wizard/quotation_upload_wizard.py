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


class QuotationUploadWizard(models.TransientModel):
    """Wizard for uploading Excel file with quotation numbers"""
    _name = 'eq.quotation.upload.wizard'
    _description = 'Quotation Excel Upload Wizard'

    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=False,
        help='Optional: Select Odoo 14 connection configuration for later status checking'
    )
    
    excel_file = fields.Binary(
        string='Excel File (.xlsx)',
        required=True,
        help='Upload Excel file with quotation numbers in first column'
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
            
            # Read quotation numbers from first column (skip header if exists)
            quotation_numbers = []
            for row in sheet.iter_rows(min_row=1, values_only=True):
                if row and row[0]:  # First column has data
                    qty_num = str(row[0]).strip()
                    if qty_num and qty_num.lower() not in ['quotation number', 'quotation', 'number']:  # Skip header
                        quotation_numbers.append(qty_num)
            
            workbook.close()
            
            if not quotation_numbers:
                raise UserError('No quotation numbers found in Excel file. Please ensure first column contains quotation numbers.')
            
            # Create migration lines (batch create - no status checking)
            MigrationLine = self.env['eq.migration.quotation']
            created_count = 0
            skipped_count = 0
            
            # Check which ones already exist (batch check)
            existing_numbers = set()
            if quotation_numbers:
                domain = [('uploaded_quotation_number', 'in', quotation_numbers)]
                if self.config_id:
                    domain.append(('config_id', '=', self.config_id.id))
                existing_records = MigrationLine.search(domain)
                existing_numbers = set(existing_records.mapped('uploaded_quotation_number'))
            
            # Create records in batch (no status check - just upload)
            lines_to_create = []
            for qty_num in quotation_numbers:
                if qty_num not in existing_numbers:
                    lines_to_create.append({
                        'uploaded_quotation_number': qty_num,
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
                'res_model': 'eq.migration.quotation',
                'view_mode': 'list,form',
                'target': 'current',
                'domain': domain,
            }
            
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error uploading Excel: %s", str(e), exc_info=True)
            raise UserError('Error uploading Excel file: %s' % str(e))
