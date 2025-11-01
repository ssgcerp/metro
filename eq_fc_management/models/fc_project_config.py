# -*- coding: utf-8 -*-

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
    
    # Common sequence number
    next_number = fields.Integer(string='Next Number', default=1, help='Common sequence number for both AMC and non-AMC projects')
    
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

    def generate_project_code(self, is_amc=False):
        """Generate project code based on configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            return False
            
        if is_amc:
            prefix = config.amc_prefix or 'AMC'
            suffix = config.amc_suffix or ''
            padding = config.amc_padding or 5
        else:
            prefix = config.non_amc_prefix or 'PROJ'
            suffix = config.non_amc_suffix or ''
            padding = config.non_amc_padding or 5
        
        # Use common sequence number
        number = config.next_number
        config.next_number += 1
        
        # Format: PREFIX + padded number + SUFFIX
        code = f"{prefix}{str(number).zfill(padding)}"
        if suffix:
            code += suffix
            
        return code

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
