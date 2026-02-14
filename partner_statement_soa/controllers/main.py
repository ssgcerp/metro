from odoo import http
from odoo.http import request
import io
import xlsxwriter
from datetime import datetime

class PartnerStatementController(http.Controller):

    @http.route('/partner_statement/xlsx/<int:wizard_id>', type='http', auth='user')
    def download_partner_statement_xlsx(self, wizard_id, **kw):
        wizard = request.env['partner.statement.wizard'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Formats
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#f0f0f0', 'border': 1})
        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        currency_format = workbook.add_format({'num_format': '#,##0.00'})
        
        data = wizard._get_report_data()
        
        for partner_id, p_data in data.items():
            partner = p_data['partner']
            worksheet = workbook.add_worksheet(partner.name[:30]) # Sheet name limit
            
            # Title & Partner Info
            worksheet.write(0, 0, "Statement of Account", title_format)
            worksheet.write(2, 0, "Partner:")
            worksheet.write(2, 1, partner.name)
            worksheet.write(3, 0, "Date:")
            worksheet.write_datetime(3, 1, wizard.date_to, date_format)
            
            # Table Header
            headers = ["Date", "Doc No.", "Ref", "Due Date", "Debit", "Credit"]
            if wizard.show_running_balance:
                headers.append("Balance")
                
            for col, header in enumerate(headers):
                worksheet.write(5, col, header, header_format)
                
            # Opening Balance
            row = 6
            worksheet.write(row, 0, "Opening Balance", workbook.add_format({'bold': True}))
            worksheet.write_number(row, 6 if wizard.show_running_balance else 5, p_data['opening_balance'], currency_format)
            row += 1
            
            # Lines
            for line in p_data['lines']:
                worksheet.write_datetime(row, 0, line['date'], date_format)
                worksheet.write(row, 1, line['move_name'] or '')
                worksheet.write(row, 2, line['ref'] or line['name'] or '')
                if line['due_date']:
                    worksheet.write_datetime(row, 3, line['due_date'], date_format)
                else:
                    worksheet.write(row, 3, '')
                    
                worksheet.write_number(row, 4, line['debit'], currency_format)
                worksheet.write_number(row, 5, line['credit'], currency_format)
                
                if wizard.show_running_balance:
                    worksheet.write_number(row, 6, line['running_balance'], currency_format)
                
                row += 1
                
            # Closing Balance
            worksheet.write(row, 0, "Closing Balance", workbook.add_format({'bold': True}))
            worksheet.write_number(row, 6 if wizard.show_running_balance else 5, p_data['closing_balance'], currency_format)
            row += 2
            
            # Aging
            if wizard.show_aging and p_data.get('aging'):
                worksheet.write(row, 0, "Aging Analysis", workbook.add_format({'bold': True}))
                row += 1
                aging_headers = ["Not Due", "0-30", "31-60", "61-90", "91-120", "120+", "Total"]
                for col, header in enumerate(aging_headers):
                    worksheet.write(row, col, header, header_format)
                row += 1
                
                aging = p_data['aging']
                worksheet.write_number(row, 0, aging['not_due'], currency_format)
                worksheet.write_number(row, 1, aging['0_30'], currency_format)
                worksheet.write_number(row, 2, aging['31_60'], currency_format)
                worksheet.write_number(row, 3, aging['61_90'], currency_format)
                worksheet.write_number(row, 4, aging['91_120'], currency_format)
                worksheet.write_number(row, 5, aging['120_plus'], currency_format)
                worksheet.write_number(row, 6, aging['total'], currency_format)
                
            worksheet.set_column(0, 0, 15)
            worksheet.set_column(1, 2, 20)
            worksheet.set_column(3, 3, 15)
            worksheet.set_column(4, 6, 12)

        workbook.close()
        output.seek(0)
        
        filename = f"Statement_{wizard.company_id.name}_{fields.Date.today()}.xlsx"
        
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )
