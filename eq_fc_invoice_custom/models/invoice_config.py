# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import re
import datetime

class AccountInvoiceConfig(models.Model):
    _name = 'account.invoice.config'
    _description = 'Account Invoice Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, default='Invoice Configuration')
    
    # Invoice Number Format Configuration
    prefix = fields.Char(string='Prefix', default='INV', required=True, help='Prefix for invoice numbers (e.g., INV)')
    module_code = fields.Char(string='Module Code', default='INV', required=True, help='Module code (e.g., INV)')
    amc_prefix = fields.Char(string='AMC Prefix', default='AMC', required=True, help='Prefix to use when AMC contract is linked (e.g., AMC)')
    use_branch_code = fields.Boolean(string='Use Branch Code', default=True, help='Include branch code in invoice number')
    use_year = fields.Boolean(string='Use Year', default=True, help='Include year in invoice number')
    padding_digits = fields.Integer(string='Padding Digits', default=4, required=True, help='Number of digits for sequential number (e.g., 4 = 0001, 1213)')
    
    # Separator
    separator = fields.Char(string='Separator', default='/', required=True, help='Separator between format parts')
    
    # Custom Format
    format_text = fields.Char(
        string='Format Text',
        help='Custom format template. Use placeholders: {prefix}, {modulecode}, {branchcode}, {nextnumber}, {year}. Example: {prefix}/{modulecode}/{branchcode}/{nextnumber}/{year}'
    )
    amc_invoice_format_text = fields.Char(
        string='Format Text for AMC Invoices',
        help='Custom format template specifically for AMC Invoices. Use placeholders: {prefix}, {modulecode}, {amcprefix}, {branchcode}, {nextnumber}, {year}. Example: {prefix}/{amcprefix}/{modulecode}/{branchcode}/{nextnumber}/{year}'
    )
    next_number = fields.Integer(
        string='Next Number',
        help='Manually set the next sequential number. Leave empty to use automatic sequence.'
    )
    
    # Vendor Bill Number Format Configuration
    bill_prefix = fields.Char(string='Bill Prefix', default='BILL', required=True, help='Prefix for vendor bill numbers (e.g., BILL)')
    bill_module_code = fields.Char(string='Bill Module Code', default='BILL', required=True, help='Module code for bills (e.g., BILL)')
    bill_padding_digits = fields.Integer(string='Bill Padding Digits', default=4, required=True, help='Number of digits for bill sequence')
    
    # Vendor Bill Custom Format
    bill_format_text = fields.Char(
        string='Bill Format Text',
        help='Custom format template for Vendor Bills. Use placeholders: {prefix}, {modulecode}, {branchcode}, {nextnumber}, {year}. Example: {prefix}/{modulecode}/{branchcode}/{nextnumber}/{year}'
    )
    bill_next_number = fields.Integer(
        string='Bill Next Number',
        help='Manually set the next sequential number for bills. Leave empty to use automatic sequence.'
    )

    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Configuration name must be unique!'),
    ]

    @api.model
    def get_config(self):
        """Get active configuration or create default"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({'name': 'Default Invoice Configuration'})
        return config
    
    def generate_invoice_number(self, branch_code=None, year=None, use_amc_format=False):
        """Generate invoice number based on configuration"""
        config = self
        
        format_text_to_use = None
        if use_amc_format:
            format_text_to_use = config.amc_invoice_format_text or None
        else:
            format_text_to_use = config.format_text or None
        
        if not format_text_to_use:
            return None
        
        if use_amc_format:
            sequence_obj = self.env['ir.sequence'].search([
                ('code', '=', 'account.invoice.sequence.amc')
            ], limit=1)
        else:
            sequence_obj = self.env['ir.sequence'].search([
                ('code', '=', 'account.invoice.sequence')
            ], limit=1)
        
        if not sequence_obj:
            sequence_name = 'Account Invoice Sequence (AMC)' if use_amc_format else 'Account Invoice Sequence'
            sequence_code = 'account.invoice.sequence.amc' if use_amc_format else 'account.invoice.sequence'
            sequence_obj = self.env['ir.sequence'].create({
                'name': sequence_name,
                'code': sequence_code,
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'number_next': 1,
                'number_increment': 1,
                'company_id': False,
            })
        
        if config.next_number and config.next_number > 0:
            sequence = config.next_number
            config.write({'next_number': sequence + 1})
        else:
            next_number = sequence_obj.next_by_id()
            try:
                sequence = int(next_number) if next_number else 1
            except (ValueError, TypeError):
                sequence = 1
        
        if use_amc_format:
            return config._generate_from_format_text(format_text_to_use, branch_code, year, sequence, config, amc_prefix=config.amc_prefix)
        else:
            return config._generate_from_format_text(format_text_to_use, branch_code, year, sequence, config)

    def generate_bill_number(self, branch_code=None, year=None):
        """Generate vendor bill number based on configuration"""
        config = self
        format_text_to_use = config.bill_format_text or None
        
        if not format_text_to_use:
            return None
            
        sequence_obj = self.env['ir.sequence'].search([
            ('code', '=', 'account.bill.sequence')
        ], limit=1)
        
        if not sequence_obj:
            sequence_obj = self.env['ir.sequence'].create({
                'name': 'Account Bill Sequence',
                'code': 'account.bill.sequence',
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'number_next': 1,
                'number_increment': 1,
                'company_id': False,
            })
            
        if config.bill_next_number and config.bill_next_number > 0:
            sequence = config.bill_next_number
            config.write({'bill_next_number': sequence + 1})
        else:
            next_number = sequence_obj.next_by_id()
            try:
                sequence = int(next_number) if next_number else 1
            except (ValueError, TypeError):
                sequence = 1
                
        # Adapt generator to use bill specific replacements
        return config._generate_bill_from_format_text(format_text_to_use, branch_code, year, sequence, config)

    def _generate_bill_from_format_text(self, format_text, branch_code, year, sequence, config):
        """Generate bill number from custom format text"""
        padded_sequence = str(sequence).zfill(config.bill_padding_digits)
        
        replacements = {
            'prefix': config.bill_prefix or '',
            'modulecode': config.bill_module_code or '',
            'branchcode': branch_code or '',
            'nextnumber': padded_sequence,
            'year': str(year) if year else '',
        }
        
        result = format_text
        for key, value in replacements.items():
            pattern = r'\{' + re.escape(key) + r'\}'
            result = re.sub(pattern, value, result, flags=re.IGNORECASE)
        
        separator = config.separator or '/'
        if separator:
            double_sep = separator + separator
            while double_sep in result:
                result = result.replace(double_sep, separator)
            result = result.strip(separator)
        
        return result
    
    def _generate_from_format_text(self, format_text, branch_code, year, sequence, config, amc_prefix=None):
        """Generate invoice number from custom format text"""
        
        padded_sequence = str(sequence).zfill(config.padding_digits)
        
        replacements = {
            'prefix': config.prefix or '',
            'modulecode': config.module_code or '',
            'branchcode': branch_code or '',
            'nextnumber': padded_sequence,
            'year': str(year) if year else '',
        }
        
        if amc_prefix is not None:
            replacements['amcprefix'] = amc_prefix or config.amc_prefix or ''
        
        result = format_text
        for key, value in replacements.items():
            pattern = r'\{' + re.escape(key) + r'\}'
            result = re.sub(pattern, value, result, flags=re.IGNORECASE)
        
        separator = config.separator or '/'
        if separator:
            double_sep = separator + separator
            while double_sep in result:
                result = result.replace(double_sep, separator)
            result = result.strip(separator)
        
        return result
