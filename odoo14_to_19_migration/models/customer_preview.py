# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CustomerPreview(models.TransientModel):
    _name = 'odoo14.customer.preview'
    _description = 'Odoo 14 Customer Preview'

    wizard_id = fields.Many2one(
        'odoo14.customer.migration.wizard',
        string='Migration Wizard',
        required=True,
        ondelete='cascade'
    )
    
    config_id = fields.Many2one(
        'odoo14.migration.config',
        string='Migration Configuration',
        required=True
    )
    
    current_index = fields.Integer(string='Current Index', default=0)
    total_count = fields.Integer(string='Total Count', default=0)
    
    display_position = fields.Char(string='Position', compute='_compute_display_position', readonly=True)
    
    @api.depends('current_index', 'total_count')
    def _compute_display_position(self):
        for record in self:
            if record.current_index is not False and record.total_count:
                record.display_position = 'Customer %s of %s' % (record.current_index + 1, record.total_count)
            else:
                record.display_position = ''
    
    # Customer fields
    customer_name = fields.Char(string='Name', readonly=True)
    customer_email = fields.Char(string='Email', readonly=True)
    customer_phone = fields.Char(string='Phone', readonly=True)
    customer_mobile = fields.Char(string='Mobile', readonly=True)
    customer_street = fields.Char(string='Street', readonly=True)
    customer_city = fields.Char(string='City', readonly=True)
    customer_state = fields.Char(string='State', readonly=True)
    customer_country = fields.Char(string='Country', readonly=True)
    customer_data_json = fields.Text(string='Full Customer Data (JSON)', readonly=True)
    
    def _clean_state_name(self, state_name):
        """Clean state name: remove (AE) and capitalize"""
        if not state_name:
            return state_name
        # Remove (AE) from state name
        cleaned = state_name.replace('(AE)', '').replace('(ae)', '').strip()
        # Capitalize first letter of each word
        cleaned = ' '.join(word.capitalize() for word in cleaned.split())
        return cleaned
    
    def _load_customer(self, offset=0):
        """Load customer data from Odoo 14"""
        self.ensure_one()
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.config_id.odoo14_url,
                db=self.config_id.odoo14_database,
                username=self.config_id.odoo14_username,
                password=self.config_id.odoo14_password
            )
            
            if not client.authenticate():
                raise UserError('Failed to authenticate with Odoo 14.')
            
            # Get customer at offset
            domain = []
            customers = client.search_read('res.partner', domain, 
                ['name', 'email', 'phone', 'mobile', 'street', 'street2', 'city', 
                 'state_id', 'zip', 'country_id', 'vat', 'is_company'], 
                limit=1, offset=offset)
            
            if not customers:
                raise UserError('No customer found at this position.')
            
            customer = customers[0]
            
            # Clean state name if present
            state_name = ''
            if customer.get('state_id'):
                state_data = customer.get('state_id')
                if isinstance(state_data, (list, tuple)) and len(state_data) > 1:
                    state_name = state_data[1]  # Get the name
                elif isinstance(state_data, dict):
                    state_name = state_data.get('name', '')
                state_name = self._clean_state_name(state_name)
            
            # Update preview with customer data
            self.write({
                'current_index': offset,
                'customer_name': customer.get('name', ''),
                'customer_email': customer.get('email', ''),
                'customer_phone': customer.get('phone', ''),
                'customer_mobile': customer.get('mobile', ''),
                'customer_street': customer.get('street', ''),
                'customer_city': customer.get('city', ''),
                'customer_state': state_name,
                'customer_country': customer.get('country_id', [False, ''])[1] if customer.get('country_id') else '',
                'customer_data_json': str(customer),
            })
            
            return True
        except Exception as e:
            _logger.error("Error loading customer: %s" % str(e))
            raise UserError('Error loading customer: %s' % str(e))
    
    def action_previous(self):
        """Navigate to previous customer"""
        self.ensure_one()
        if self.current_index <= 0:
            raise UserError('This is the first customer.')
        
        new_index = self.current_index - 1
        self._load_customer(offset=new_index)
        
        # Update current_index to show correct position (1-based for display)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Preview (%s of %s)' % (self.current_index + 1, self.total_count),
            'res_model': 'odoo14.customer.preview',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }
    
    def action_next(self):
        """Navigate to next customer"""
        self.ensure_one()
        if self.current_index >= self.total_count - 1:
            raise UserError('This is the last customer.')
        
        new_index = self.current_index + 1
        self._load_customer(offset=new_index)
        
        # Update current_index to show correct position (1-based for display)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Preview (%s of %s)' % (self.current_index + 1, self.total_count),
            'res_model': 'odoo14.customer.preview',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
        }

