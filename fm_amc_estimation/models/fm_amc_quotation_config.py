# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FMAMCQuotationConfig(models.Model):
    _name = 'fm.amc.quotation.config'
    _description = 'FM AMC Quotation Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, default='Quotation Numbering Configuration')
    
    # Quotation Number Format Configuration
    prefix = fields.Char(string='Prefix', default='QUO', required=True, help='Prefix for quotation numbers (e.g., QUO)')
    module_code = fields.Char(string='Module Code', default='QUO', required=True, help='Module code (e.g., QUO)')
    amc_prefix = fields.Char(string='AMC Prefix', default='AMC', required=True, help='Prefix to use when AMC contract is linked (e.g., AMC)')
    use_branch_code = fields.Boolean(string='Use Branch Code', default=True, help='Include branch code in quotation number')
    use_year = fields.Boolean(string='Use Year', default=True, help='Include year in quotation number')
    padding_digits = fields.Integer(string='Padding Digits', default=4, required=True, help='Number of digits for sequential number (e.g., 4 = 0001, 1213)')
    
    # Separator
    separator = fields.Char(string='Separator', default='/', required=True, help='Separator between format parts')
    
    # Custom Format
    format_text = fields.Char(
        string='Format Text',
        help='Custom format template. Use placeholders: {prefix}, {modulecode}, {branchcode}, {nextnumber}, {year}. Example: {prefix}/{modulecode}/{branchcode}/{nextnumber}/{year}'
    )
    amc_quotation_format_text = fields.Char(
        string='Format Text for AMC Quotations',
        help='Custom format template specifically for AMC Quotations. Use placeholders: {prefix}, {modulecode}, {branchcode}, {nextnumber}, {year}. Example: {prefix}/{modulecode}/{branchcode}/{nextnumber}/{year}'
    )
    next_number = fields.Integer(
        string='Next Number',
        help='Manually set the next sequential number. Leave empty to use automatic sequence.'
    )
    
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Configuration name must be unique!'),
    ]

    def generate_quotation_number(self, branch_code=None, year=None, use_amc_format=False):
        """Generate quotation number based on configuration
        
        Args:
            branch_code: Branch code to include in the number
            year: Year to include in the number
            use_amc_format: If True, use AMC quotation format (when AMC contract is linked)
        
        If format_text is set, use it with placeholders.
        Otherwise, use the standard format: [PREFIX]/[MODULE_CODE]/[BRANCH_CODE]/[SEQUENTIAL]/[YEAR]
        Example: QUO/QUO/FUJ/1213/2025
        """
        # Use self as config (the record calling this method)
        config = self
        
        # Get sequence number based on whether this is an AMC quotation or not
        if use_amc_format and config.amc_quotation_format_text:
            # Use AMC quotation sequence
            sequence_obj = self.env['ir.sequence'].search([
                ('code', '=', 'fm.amc.quotation.sequence.amc')
            ], limit=1)
        else:
            # Use standard quotation sequence
            sequence_obj = self.env['ir.sequence'].search([
                ('code', '=', 'fm.amc.quotation.sequence')
            ], limit=1)
        
        if not sequence_obj:
            # Create the appropriate sequence if it doesn't exist
            sequence_name = 'FM AMC Quotation Sequence (AMC)' if use_amc_format else 'FM AMC Quotation Sequence'
            sequence_code = 'fm.amc.quotation.sequence.amc' if use_amc_format else 'fm.amc.quotation.sequence'
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
            # Update next_number for next use
            config.write({'next_number': sequence + 1})
        else:
            next_number = sequence_obj.next_by_id()
            # Convert to integer
            try:
                sequence = int(next_number) if next_number else 1
            except (ValueError, TypeError):
                sequence = 1
        
        # If use_amc_format is True and AMC quotation format text is provided, use it
        if use_amc_format and config.amc_quotation_format_text:
            # Pass AMC prefix for AMC quotations
            return config._generate_from_format_text(config.amc_quotation_format_text, branch_code, year, sequence, config, amc_prefix=config.amc_prefix)
        
        # If custom format text is provided, use it
        if config.format_text:
            return config._generate_from_format_text(config.format_text, branch_code, year, sequence, config)
        
        # Otherwise use the standard format
        # Build quotation number parts
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
        quotation_number = separator.join(parts)
        
        return quotation_number
    
    @api.model
    def get_config(self):
        """Get the active configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            # Create default configuration
            config = self.create({
                'name': 'Default Quotation Configuration',
            })
        return config
    
    def _generate_from_format_text(self, format_text, branch_code, year, sequence, config, amc_prefix=None):
        """Generate quotation number from custom format text
        
        Replace placeholders in format_text:
        - {prefix} or {PREFIX}
        - {modulecode} or {MODULECODE}
        - {amcprefix} or {AMCPREFIX} - AMC prefix (if provided)
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
        
        # Add AMC prefix if provided
        if amc_prefix is not None:
            replacements['amcprefix'] = amc_prefix or config.amc_prefix or ''
        
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
        """Get next sequence number for quotation"""
        # Store sequence in ir.sequence or use a simple counter
        sequence_obj = self.env['ir.sequence'].search([
            ('code', '=', 'fm.amc.quotation.sequence')
        ], limit=1)
        
        if not sequence_obj:
            sequence_obj = self.env['ir.sequence'].create({
                'name': 'FM AMC Quotation Sequence',
                'code': 'fm.amc.quotation.sequence',
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
