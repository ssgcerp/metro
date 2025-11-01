# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FMAMCProductSKUConfig(models.Model):
    _name = 'fm.amc.product.sku.config'
    _description = 'FM AMC Product SKU Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', required=True, default='Product SKU Configuration')
    
    # Product SKU Configuration
    estimation_sku_prefix = fields.Char(string='Estimation SKU Prefix', default='EST-SKU', required=True, help='Prefix for estimation SKUs (e.g., EST-SKU)')
    default_sku_prefix = fields.Char(string='Default SKU Prefix', default='SKU', required=True, help='Prefix for default product SKUs (e.g., SKU)')
    sku_padding_digits = fields.Integer(string='SKU Padding Digits', default=6, required=True, help='Number of digits for sequential SKU number (e.g., 6 = 000001)')
    sku_separator = fields.Char(string='SKU Separator', default='-', required=True, help='Separator between SKU prefix and number (e.g., -)')
    estimation_sku_next_number = fields.Integer(string='Estimation SKU Next Number', help='Manually set the next sequential estimation SKU number. Leave empty to use automatic sequence.')
    default_sku_next_number = fields.Integer(string='Default SKU Next Number', help='Manually set the next sequential default SKU number. Leave empty to use automatic sequence.')
    
    active = fields.Boolean(string='Active', default=True)

    def _get_sequence_code(self, sku_type='estimation'):
        """Get or create sequence code"""
        return 'fm.amc.%s.sku.sequence' % sku_type

    @api.model
    def get_config(self):
        """Get active configuration or create default"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({'name': 'Default Product SKU Configuration'})
        return config

    def generate_estimation_sku(self):
        """Generate new estimation SKU"""
        self.ensure_one()
        config = self
        
        # Get sequence code
        sequence_code = self._get_sequence_code('estimation')
        sequence_obj = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
        
        # Create sequence if not exists
        if not sequence_obj:
            sequence_obj = self.env['ir.sequence'].create({
                'name': 'FM AMC Estimation SKU Sequence',
                'code': sequence_code,
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'number_next': 1,
                'number_increment': 1,
                'company_id': False,
            })
        
        # Get next sequence number
        if config.estimation_sku_next_number and config.estimation_sku_next_number > 0:
            sequence = config.estimation_sku_next_number
            config.write({'estimation_sku_next_number': sequence + 1})
        else:
            next_number = sequence_obj.next_by_id()
            try:
                sequence = int(next_number) if next_number else 1
            except (ValueError, TypeError):
                sequence = 1
        
        # Format SKU
        padded_sequence = str(sequence).zfill(config.sku_padding_digits)
        separator = config.sku_separator or '-'
        sku = f"{config.estimation_sku_prefix}{separator}{padded_sequence}"
        return sku
    
    def generate_default_sku(self):
        """Generate new default SKU"""
        self.ensure_one()
        config = self
        
        # Get sequence code
        sequence_code = self._get_sequence_code('default')
        sequence_obj = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
        
        # Create sequence if not exists
        if not sequence_obj:
            sequence_obj = self.env['ir.sequence'].create({
                'name': 'FM AMC Product SKU Sequence',
                'code': sequence_code,
                'prefix': '',
                'suffix': '',
                'padding': 0,
                'number_next': 1,
                'number_increment': 1,
                'company_id': False,
            })
        
        # Get next sequence number
        if config.default_sku_next_number and config.default_sku_next_number > 0:
            sequence = config.default_sku_next_number
            config.write({'default_sku_next_number': sequence + 1})
        else:
            next_number = sequence_obj.next_by_id()
            try:
                sequence = int(next_number) if next_number else 1
            except (ValueError, TypeError):
                sequence = 1
        
        # Format SKU
        padded_sequence = str(sequence).zfill(config.sku_padding_digits)
        separator = config.sku_separator or '-'
        sku = f"{config.default_sku_prefix}{separator}{padded_sequence}"
        return sku

