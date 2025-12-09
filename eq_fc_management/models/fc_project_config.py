# -*- coding: utf-8 -*-

import re
from datetime import date, datetime

from odoo import models, fields, api


class FCProjectConfig(models.Model):
    _name = 'fc.project.config'
    _description = 'Project Financial Control Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, default='Project Numbering Configuration')
    
    # AMC Project Configuration
    amc_prefix = fields.Char(string='AMC Prefix', default='AMC', help='Prefix for AMC projects')
    amc_suffix = fields.Char(string='AMC Suffix', default='', help='Suffix for AMC projects')
    amc_padding = fields.Integer(string='AMC Padding Digits', default=5, help='Number of padding digits for AMC projects')
    
    # Non-AMC Project Configuration
    non_amc_prefix = fields.Char(string='Non-AMC Prefix', default='PROJ', help='Prefix for non-AMC projects')
    non_amc_suffix = fields.Char(string='Non-AMC Suffix', default='', help='Suffix for non-AMC projects')
    non_amc_padding = fields.Integer(string='Non-AMC Padding Digits', default=5, help='Number of padding digits for non-AMC projects')
    amc_format_text = fields.Char(
        string='AMC Format Text',
        help=(
            'Custom format template for project numbers. '
            'Use placeholders: {prefix}, {modulecode}, {branchcode}, {nextnumber}, {year}. '
            'Example: {prefix}/{modulecode}/{branchcode}/{nextnumber}/{year}'
        )
    )
    non_amc_format_text = fields.Char(
        string='Non-AMC Format Text',
        help=(
            'Custom format template for project numbers. '
            'Use placeholders: {prefix}, {modulecode}, {branchcode}, {nextnumber}, {year}. '
            'Example: {prefix}-{branchcode}-{nextnumber}-{year}'
        )
    )
    
    # Common sequence number
    next_number = fields.Integer(string='Next Number', default=1, help='Common sequence number for both AMC and non-AMC projects')
    include_branch_code = fields.Boolean(
        string='Include Branch Code',
        default=True,
        help='Add branch/company code to the default numbering when no format text is provided.'
    )
    include_year = fields.Boolean(
        string='Include Year',
        default=True,
        help='Add project year to the default numbering when no format text is provided.'
    )
    
    # Profit threshold configuration
    profit_warning_threshold = fields.Float(string='Profit Warning Threshold (%)', default=10.0, help='Profit percentage below which label turns yellow')
    profit_danger_threshold = fields.Float(string='Profit Danger Threshold (%)', default=5.0, help='Profit percentage below which label turns red')
    
    # Cost overrun configuration
    cost_warning_threshold = fields.Float(string='Cost Warning Threshold (%)', default=10.0, help='Cost overrun percentage above which label turns orange')
    cost_danger_threshold = fields.Float(string='Cost Danger Threshold (%)', default=20.0, help='Cost overrun percentage above which label turns red')
    
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Configuration name must be unique!'),
    ]

    def generate_project_code(self, project=None, is_amc=False):
        """Generate project code based on configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            return False

        if is_amc:
            prefix = config.amc_prefix or 'AMC'
            suffix = config.amc_suffix or ''
            padding = config.amc_padding or 5
            module_code = 'AMC'
            format_text = config.amc_format_text or ''
        else:
            prefix = config.non_amc_prefix or 'PROJ'
            suffix = config.non_amc_suffix or ''
            padding = config.non_amc_padding or 5
            module_code = 'PROJ'
            format_text = config.non_amc_format_text or ''

        # Use common sequence number
        number = config.next_number or 1
        config.next_number = number + 1

        padded_number = str(number).zfill(padding)

        branch_code = ''
        if project:
            branch = getattr(project, 'branch_id', False)
            if branch and getattr(branch, 'code', False):
                branch_code = branch.code
            elif project.company_id:
                branch_code = getattr(project.company_id, 'code', '') or (project.company_id.name or '')[:3].upper()

        project_year = ''
        project_date = None
        if project:
            project_date = getattr(project, 'date_start', False) or getattr(project, 'create_date', False)
        if not project_date:
            project_date = fields.Date.context_today(self)
        if isinstance(project_date, str):
            project_year = fields.Date.to_date(project_date).year
        elif isinstance(project_date, datetime):
            project_year = project_date.year
        elif isinstance(project_date, date):
            project_year = project_date.year
        else:
            project_year = fields.Date.context_today(self).year

        replacements = {
            'prefix': prefix or '',
            'modulecode': module_code or '',
            'branchcode': branch_code or '',
            'nextnumber': padded_number,
            'year': str(project_year) if project_year else '',
            'suffix': suffix or '',
        }

        if format_text:
            code = self._generate_from_format_text(format_text, replacements)
            if suffix and '{suffix}' not in format_text.lower():
                code = f"{code}{suffix}"
        else:
            # Default format with optional branch code and year
            parts = []
            if prefix:
                parts.append(prefix)
            include_branch = config.include_branch_code and branch_code
            if include_branch:
                parts.append(branch_code)
            parts.append(padded_number)
            include_year = config.include_year and project_year
            if include_year:
                parts.append(str(project_year))

            if include_branch or include_year:
                code = '/'.join(filter(None, parts))
            else:
                code = f"{prefix or ''}{padded_number}"
            if suffix:
                code = f"{code}{suffix}"

        return code

    def _generate_from_format_text(self, format_text, replacements):
        """Generate code from custom format text using case-insensitive placeholders."""
        result = format_text or ''
        for key, value in replacements.items():
            pattern = r'\{' + re.escape(key) + r'\}'
            result = re.sub(pattern, value, result, flags=re.IGNORECASE)

        # Clean up double separators like '//' or '--' if present
        # Simple normalization to remove duplicate non-alphanumeric separators
        result = re.sub(r'([^\w\s])\1+', r'\1', result)
        return result.strip()

    @api.model
    def get_config(self):
        """Get the active configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            # Create default configuration
            config = self.create({
                'name': 'Default Project Configuration',
            })
        return config
