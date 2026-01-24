# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    """Extend account.move (Customer Invoices) with custom fields"""
    _inherit = 'account.move'

    # Custom fields for customer invoices
    location = fields.Char(string='Location', help="Location information")
    site_name = fields.Char(string='Site Name', help="Site name for the invoice")
    create_do = fields.Boolean(string='Create DO', default=False, help="Create Delivery Order")
    bank_details = fields.Text(string='Bank Details', help="Bank details information")
    file_to_upload = fields.Binary(string='File', help="File to upload")
    filename = fields.Char(string='Filename', help="Name of the uploaded file")
    in_note = fields.Text(string='Invoice Note', help="Additional notes for the invoice")
    
    # AMC Contract - Selection field filtered by customer
    # Using Many2one which appears as a selection dropdown in the UI
    amc_contract_id = fields.Many2one(
        'amc.contract',
        string='AMC Contract',
        domain="[('customer_id', '=', partner_id)]",
        help="AMC Contract for this customer. Only contracts for the selected customer are shown."
    )
    
    move_line_ids = fields.One2many(related='line_ids', string='Journal Items (Legacy Alias)')

    @api.model_create_multi
    def create(self, vals_list):
        """Generate Invoice Number based on Configuration"""
        for vals in vals_list:
            if vals.get('move_type') == 'out_invoice' and vals.get('name', '/') == '/':
                # Get Branch Code
                branch_code = ''
                if vals.get('journal_id'):
                    journal = self.env['account.journal'].browse(vals['journal_id'])
                    # Try to get branch code from journal name or code
                    # Or check for explicit branch field in context/vals if any
                    if 'BR' in journal.code:
                         branch_code = journal.code
                    else:
                         branch_code = journal.code

                year = fields.Date.today().year
                
                # Check for AMC contract to decide format
                use_amc = False
                if vals.get('amc_contract_id'):
                    use_amc = True
                
                # Get Config
                config = self.env['account.invoice.config'].get_config()
                if config:
                    new_ref = config.generate_invoice_number(branch_code=branch_code, year=year, use_amc_format=use_amc)
                    if new_ref:
                        vals['name'] = new_ref

        return super().create(vals_list)

    def action_post(self):
        """Generates custom invoice number on posting if not already set"""
        for move in self:
            if move.state == 'posted':
                continue
                
            # Customer Invoice Generation
            if move.move_type == 'out_invoice' and (move.name == '/' or move.name == 'Draft' or not move.name):
                # Get Branch Code from Company
                branch_code = ''
                if move.company_id and move.company_id.branch_code:
                    branch_code = move.company_id.branch_code
                elif move.journal_id and 'BR' in move.journal_id.code:
                    # Fallback to legcay journal code logic if needed, but company field is preferred
                    branch_code = move.journal_id.code
                
                year = move.date.year if move.date else fields.Date.today().year
                
                # Check for AMC contract
                use_amc = bool(move.amc_contract_id)
                
                config = self.env['account.invoice.config'].get_config()
                if config:
                    new_ref = config.generate_invoice_number(branch_code=branch_code, year=year, use_amc_format=use_amc)
                    if new_ref:
                        move.write({'name': new_ref})
            
            # Vendor Bill Generation
            elif move.move_type == 'in_invoice' and (move.name == '/' or move.name == 'Draft' or not move.name):
                # Get Branch Code from Company or Journal
                branch_code = ''
                if move.company_id and move.company_id.branch_code:
                    branch_code = move.company_id.branch_code
                elif move.journal_id and 'BR' in move.journal_id.code:
                    branch_code = move.journal_id.code
                elif move.company_id and move.company_id.name:
                    # Fallback to first 3 letters of company name if branch_code is missing
                    branch_code = move.company_id.name[:3].upper()
                
                year = move.date.year if move.date else fields.Date.today().year
                
                config = self.env['account.invoice.config'].get_config()
                if config:
                    new_ref = config.generate_bill_number(branch_code=branch_code, year=year)
                    if new_ref:
                         move.write({'name': new_ref})
        
        return super().action_post()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Clear AMC Contract when customer changes"""
        self.amc_contract_id = False

