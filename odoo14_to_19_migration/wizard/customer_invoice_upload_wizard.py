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


class CustomerInvoiceUploadWizard(models.TransientModel):
    """Wizard for uploading Excel file with customer invoice numbers"""
    _name = 'customer.invoice.upload.wizard'
    _description = 'Customer Invoice Excel Upload Wizard'

    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=False,
        help='Optional: Select Odoo 14 connection configuration for later status checking'
    )
    
    excel_file = fields.Binary(
        string='Excel File (.xlsx)',
        required=True,
        help='Upload Excel file with invoice numbers and related data'
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
            
            # Expected columns: Number, Voucher Number, Invoice Partner Name, Invoice/Bill Date, 
            # Due Date, Status, Payment Status, Company, Quote Reference
            rows_data = []
            header_row = None
            column_indices = {}  # Map column names to indices
            
            # First pass: Find header row and column indices
            for row_idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=20, values_only=True), start=1):
                if not row or not any(row):
                    continue
                
                # Check if this is a header row
                row_lower = [str(cell).strip().lower() if cell else '' for cell in row]
                
                # Look for key header words
                if any(keyword in ' '.join(row_lower) for keyword in ['number', 'invoice', 'voucher', 'partner', 'date', 'status', 'payment', 'company', 'quote']):
                    header_row = row_idx
                    # Map column names to indices
                    for col_idx, cell_value in enumerate(row):
                        cell_str = str(cell_value).strip().lower() if cell_value else ''
                        if 'number' in cell_str and 'voucher' not in cell_str and 'invoice' not in cell_str:
                            column_indices['number'] = col_idx
                        elif 'voucher' in cell_str:
                            column_indices['voucher_number'] = col_idx
                        elif 'partner' in cell_str or 'customer' in cell_str:
                            column_indices['invoice_partner_name'] = col_idx
                        elif 'invoice' in cell_str and 'date' in cell_str or 'bill' in cell_str and 'date' in cell_str:
                            column_indices['invoice_bill_date'] = col_idx
                        elif 'due' in cell_str and 'date' in cell_str:
                            column_indices['due_date'] = col_idx
                        elif 'status' in cell_str and 'payment' not in cell_str:
                            column_indices['status'] = col_idx
                        elif 'payment' in cell_str and 'status' in cell_str:
                            column_indices['payment_status'] = col_idx
                        elif 'company' in cell_str or 'branch' in cell_str:
                            column_indices['company'] = col_idx
                        elif 'quote' in cell_str and 'reference' in cell_str:
                            column_indices['quote_reference'] = col_idx
                    break
            
            # Second pass: Extract data
            start_row = header_row + 1 if header_row else 1
            for row_idx, row in enumerate(sheet.iter_rows(min_row=start_row, values_only=True), start=start_row):
                if not row or not any(row):
                    continue
                
                # Extract data from columns
                number = str(row[column_indices.get('number', 0)]).strip() if column_indices.get('number', 0) < len(row) and row[column_indices.get('number', 0)] else ''
                voucher_number = str(row[column_indices.get('voucher_number', 1)]).strip() if column_indices.get('voucher_number', 1) < len(row) and row[column_indices.get('voucher_number', 1)] else ''
                invoice_partner_name = str(row[column_indices.get('invoice_partner_name', 2)]).strip() if column_indices.get('invoice_partner_name', 2) < len(row) and row[column_indices.get('invoice_partner_name', 2)] else ''
                invoice_bill_date = row[column_indices.get('invoice_bill_date', 3)] if column_indices.get('invoice_bill_date', 3) < len(row) and row[column_indices.get('invoice_bill_date', 3)] else None
                due_date = row[column_indices.get('due_date', 4)] if column_indices.get('due_date', 4) < len(row) and row[column_indices.get('due_date', 4)] else None
                excel_status = str(row[column_indices.get('status', 5)]).strip() if column_indices.get('status', 5) < len(row) and row[column_indices.get('status', 5)] else ''
                payment_status = str(row[column_indices.get('payment_status', 6)]).strip() if column_indices.get('payment_status', 6) < len(row) and row[column_indices.get('payment_status', 6)] else ''
                company = str(row[column_indices.get('company', 7)]).strip() if column_indices.get('company', 7) < len(row) and row[column_indices.get('company', 7)] else ''
                quote_reference = str(row[column_indices.get('quote_reference', 8)]).strip() if column_indices.get('quote_reference', 8) < len(row) and row[column_indices.get('quote_reference', 8)] else ''
                
                # Only add rows with invoice number
                if number and number.lower() not in ('number', 'n/a', 'none', 'null', ''):
                    # Parse dates
                    invoice_date = None
                    if invoice_bill_date:
                        if isinstance(invoice_bill_date, str):
                            try:
                                from datetime import datetime
                                invoice_date = datetime.strptime(invoice_bill_date.split()[0], '%Y-%m-%d').date()
                            except:
                                pass
                        else:
                            invoice_date = invoice_bill_date
                    
                    due_date_parsed = None
                    if due_date:
                        if isinstance(due_date, str):
                            try:
                                from datetime import datetime
                                due_date_parsed = datetime.strptime(due_date.split()[0], '%Y-%m-%d').date()
                            except:
                                pass
                        else:
                            due_date_parsed = due_date
                    
                    rows_data.append({
                        'number': number,
                        'voucher_number': voucher_number if voucher_number and voucher_number.lower() not in ('n/a', 'none', 'null', '') else '',
                        'invoice_partner_name': invoice_partner_name if invoice_partner_name and invoice_partner_name.lower() not in ('n/a', 'none', 'null', '') else '',
                        'invoice_bill_date': invoice_date,
                        'due_date': due_date_parsed,
                        'excel_status': excel_status if excel_status and excel_status.lower() not in ('n/a', 'none', 'null', '') else '',
                        'payment_status': payment_status if payment_status and payment_status.lower() not in ('n/a', 'none', 'null', '') else '',
                        'company': company if company and company.lower() not in ('n/a', 'none', 'null', '') else '',
                        'quote_reference': quote_reference if quote_reference and quote_reference.lower() not in ('n/a', 'none', 'null', '') else '',
                    })
            
            workbook.close()
            
            if not rows_data:
                raise UserError('No invoice data found in Excel file. Please ensure the file has the correct columns: Number, Voucher Number, Invoice Partner Name, Invoice/Bill Date, Due Date, Status, Payment Status, Company, Quote Reference')
            
            # Create migration lines (batch create)
            MigrationLine = self.env['customer.invoice.migration.line']
            created_count = 0
            skipped_count = 0
            
            # Get all invoice numbers from uploaded data
            invoice_numbers = [r['number'] for r in rows_data]
            
            # Check which ones already exist (batch check)
            existing_numbers = set()
            if invoice_numbers:
                domain = [('uploaded_invoice_number', 'in', invoice_numbers)]
                if self.config_id:
                    domain.append(('config_id', '=', self.config_id.id))
                existing_records = MigrationLine.search(domain)
                existing_numbers = set(existing_records.mapped('uploaded_invoice_number'))
            
            # Create records in batch with all fields
            lines_to_create = []
            for row_data in rows_data:
                inv_num = row_data['number']
                if inv_num not in existing_numbers:
                    lines_to_create.append({
                        'uploaded_invoice_number': inv_num,
                        'voucher_number': row_data['voucher_number'],
                        'invoice_partner_name': row_data['invoice_partner_name'],
                        'invoice_bill_date': row_data['invoice_bill_date'],
                        'due_date': row_data['due_date'],
                        'excel_status': row_data['excel_status'],
                        'payment_status': row_data['payment_status'],
                        'company': row_data['company'],
                        'quote_reference': row_data['quote_reference'],
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
                'res_model': 'customer.invoice.migration.line',
                'view_mode': 'list,form',
                'target': 'current',
                'domain': domain,
            }
            
        except UserError:
            raise
        except Exception as e:
            _logger.error("Error uploading Excel: %s", str(e), exc_info=True)
            raise UserError('Error uploading Excel file: %s' % str(e))

