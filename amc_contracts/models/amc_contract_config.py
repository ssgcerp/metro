# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AMCContractConfig(models.Model):
    _name = 'amc.contract.config'
    _description = 'AMC Contract Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, default='AMC Contract Numbering Configuration')
    
    # Contract Number Format Configuration
    prefix = fields.Char(string='Prefix', default='MFS', required=True, help='Prefix for AMC contract numbers (e.g., MFS)')
    module_code = fields.Char(string='Module Code', default='AMC', required=True, help='Module code (e.g., AMC)')
    use_branch_code = fields.Boolean(string='Use Branch Code', default=True, help='Include branch code in contract number')
    use_year = fields.Boolean(string='Use Year', default=True, help='Include year in contract number')
    padding_digits = fields.Integer(string='Padding Digits', default=4, required=True, help='Number of digits for sequential number (e.g., 4 = 0001, 1213)')
    
    # Separator
    separator = fields.Char(string='Separator', default='/', required=True, help='Separator between format parts')
    
    # Custom Format
    format_text = fields.Char(
        string='Format Text',
        help='Custom format template. Use placeholders: {prefix}, {modulecode}, {branchcode}, {nextnumber}, {year}. Example: {prefix}/{modulecode}/{branchcode}/{nextnumber}/{year}'
    )
    next_number = fields.Integer(
        string='Next Number',
        help='Manually set the next sequential number. Leave empty to use automatic sequence.'
    )
    
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Configuration name must be unique!'),
    ]

    def generate_contract_number(self, branch_code=None, year=None):
        """Generate contract number based on configuration
        
        If format_text is set, use it with placeholders.
        Otherwise, use the standard format: [PREFIX]/[MODULE_CODE]/[BRANCH_CODE]/[SEQUENTIAL]/[YEAR]
        Example: MFS/AMC/FUJ/1213/2025
        """
        config = self.get_config()
        
        # Get sequence number (use next_number if set, otherwise auto-increment)
        if config.next_number and config.next_number > 0:
            sequence = config.next_number
            # Update next_number for next use
            config.write({'next_number': sequence + 1})
        else:
            sequence = self._get_next_sequence()
        
        # If custom format text is provided, use it
        if config.format_text:
            return self._generate_from_format_text(config.format_text, branch_code, year, sequence, config)
        
        # Otherwise use the standard format
        # Build contract number parts
        parts = []
        
        # Add prefix
        if config.prefix:
            parts.append(config.prefix)
        
        # Add module code
        if config.module_code:
            parts.append(config.module_code)
        
        # Add branch code if enabled and provided
        if config.use_branch_code and branch_code:
            parts.append(branch_code)
        
        # Add padded sequence number
        padded_sequence = str(sequence).zfill(config.padding_digits)
        parts.append(padded_sequence)
        
        # Add year if enabled and provided
        if config.use_year and year:
            parts.append(str(year))
        
        # Join with separator
        separator = config.separator or '/'
        contract_number = separator.join(parts)
        
        return contract_number
    
    def _generate_from_format_text(self, format_text, branch_code, year, sequence, config):
        """Generate contract number from custom format text
        
        Replace placeholders in format_text:
        - {prefix} or {PREFIX}
        - {modulecode} or {MODULECODE}
        - {branchcode} or {BRANCHCODE}
        - {nextnumber} or {NEXTNUMBER}
        - {year} or {YEAR}
        """
        import re
        
        # Get padded sequence
        padded_sequence = str(sequence).zfill(config.padding_digits)
        
        # Prepare replacement values
        replacements = {
            'prefix': config.prefix or '',
            'modulecode': config.module_code or '',
            'branchcode': branch_code or '',
            'nextnumber': padded_sequence,
            'year': str(year) if year else '',
        }
        
        # Replace placeholders (case-insensitive)
        result = format_text
        for key, value in replacements.items():
            # Replace both {key} and {KEY} patterns
            pattern = r'\{' + re.escape(key) + r'\}'
            result = re.sub(pattern, value, result, flags=re.IGNORECASE)
        
        # Clean up any empty sections (double separators)
        separator = config.separator or '/'
        if separator:
            # Remove double separators
            double_sep = separator + separator
            while double_sep in result:
                result = result.replace(double_sep, separator)
            # Remove leading/trailing separators
            result = result.strip(separator)
        
        return result

    def _get_next_sequence(self):
        """Get next sequence number for contract"""
        # Store sequence in ir.sequence or use a simple counter
        sequence_obj = self.env['ir.sequence'].search([
            ('code', '=', 'amc.contract.sequence')
        ], limit=1)
        
        if not sequence_obj:
            sequence_obj = self.env['ir.sequence'].create({
                'name': 'AMC Contract Sequence',
                'code': 'amc.contract.sequence',
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'number_next': 1,
                'number_increment': 1,
                'company_id': False,
            })
        
        next_number = sequence_obj.next_by_id()
        # Convert to integer (remove any prefix/suffix padding that was added)
        # Since we're using padding 0, it should be just the number
        try:
            return int(next_number) if next_number else 1
        except (ValueError, TypeError):
            return 1

    @api.model
    def get_config(self):
        """Get the active configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            # Create default configuration
            config = self.create({
                'name': 'Default AMC Configuration',
            })
        return config

