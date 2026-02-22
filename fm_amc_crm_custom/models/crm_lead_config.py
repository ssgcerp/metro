# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CrmLeadConfig(models.Model):
    _name = 'crm.lead.config'
    _description = 'Lead Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, default='Lead Configuration')
    
    # Lead Sequence Format Configuration
    prefix = fields.Char(string='Prefix', default='L', required=True, help='Prefix for lead numbers (e.g., L)')
    module_code = fields.Char(string='Module Code', default='L', required=True, help='Module code (e.g., L)')
    use_branch_code = fields.Boolean(string='Use Branch Code', default=True, help='Include branch code in lead number')
    use_year = fields.Boolean(string='Use Year', default=True, help='Include year in lead number')
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

    @api.model
    def get_config(self):
        """Get active configuration or create default"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({'name': 'Default Lead Configuration'})
        return config
    
    def generate_lead_sequence(self, branch_code=None, year=None, force_sequence_number=None):
        """Generate lead sequence based on configuration
        
        Args:
            branch_code: Branch code to include in the number
            year: Year to include in the number
        
        Returns:
            Custom lead sequence string if format_text is configured, None otherwise
        """
        config = self
        
        # Check if custom format is configured
        format_text_to_use = config.format_text or None
        
        # If no custom format is specified, try to build default
        if not format_text_to_use:
            # {prefix}/{modulecode}/{branchcode}/{nextnumber}/{year}
            parts = []
            if config.prefix: parts.append('{prefix}')
            if config.module_code: parts.append('{modulecode}')
            if config.use_branch_code: parts.append('{branchcode}')
            parts.append('{nextnumber}')
            if config.use_year: parts.append('{year}')
            format_text_to_use = (config.separator or '/').join(parts)
        
        # Get sequence number
        sequence_obj = self.env['ir.sequence'].search([
            ('code', '=', 'crm.lead.sequence')
        ], limit=1)
        
        if not sequence_obj:
            # Create the required sequence if it doesn't exist
            sequence_obj = self.env['ir.sequence'].create({
                'name': 'CRM Lead Sequence',
                'code': 'crm.lead.sequence',
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'number_next': 1,
                'number_increment': 1,
                'company_id': False,
            })
        
        if force_sequence_number:
            sequence = force_sequence_number
        elif config.next_number and config.next_number > 0:
            sequence = config.next_number
            # Update next_number for next use
            config.write({'next_number': sequence + 1})
        else:
            next_number = sequence_obj.next_by_id()
            try:
                sequence = int(next_number) if next_number else 1
            except (ValueError, TypeError):
                sequence = 1
        
        return config._generate_from_format_text(format_text_to_use, branch_code, year, sequence, config)
    
    def _generate_from_format_text(self, format_text, branch_code, year, sequence, config):
        """Generate number from custom format text
        
        Replace placeholders in format_text:
        - {prefix}
        - {modulecode}
        - {branchcode}
        - {nextnumber}
        - {year}
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
            pattern = r'\{' + re.escape(key) + r'\}'
            result = re.sub(pattern, value, result, flags=re.IGNORECASE)
        
        # Clean up any empty sections (double separators)
        separator = config.separator or '/'
        if separator:
            double_sep = separator + separator
            while double_sep in result:
                result = result.replace(double_sep, separator)
            result = result.strip(separator)
        
        return result
