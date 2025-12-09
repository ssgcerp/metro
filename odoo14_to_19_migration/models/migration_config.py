# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MigrationConfig(models.Model):
    _name = 'odoo14.migration.config'
    _description = 'Odoo 14 Migration Configuration'
    _rec_name = 'odoo14_url'

    odoo14_url = fields.Char(
        string='Odoo 14 URL',
        required=True,
        help='Full URL of the Odoo 14 instance (e.g., http://odoo14.example.com)'
    )
    odoo14_username = fields.Char(
        string='Username',
        required=True,
        help='Username for Odoo 14 API connection'
    )
    odoo14_password = fields.Char(
        string='Password',
        required=True,
        help='Password for Odoo 14 API connection'
    )
    odoo14_database = fields.Char(
        string='Database',
        required=True,
        help='Database name in Odoo 14 instance'
    )
    connection_status = fields.Char(
        string='Connection Status',
        readonly=True,
        help='Last connection test result'
    )
    last_connection_test = fields.Datetime(
        string='Last Connection Test',
        readonly=True
    )

    def test_connection(self):
        """Test connection to Odoo 14 instance"""
        self.ensure_one()
        try:
            from ..models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=self.odoo14_url,
                db=self.odoo14_database,
                username=self.odoo14_username,
                password=self.odoo14_password
            )
            
            if client.authenticate():
                self.write({
                    'connection_status': 'Connected',
                    'last_connection_test': fields.Datetime.now()
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection Successful',
                        'message': 'Successfully connected to Odoo 14 instance.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                self.write({
                    'connection_status': 'Failed',
                    'last_connection_test': fields.Datetime.now()
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection Failed',
                        'message': 'Failed to connect to Odoo 14 instance. Please check your credentials.',
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        except Exception as e:
            _logger.error(f"Connection test error: {str(e)}")
            self.write({
                'connection_status': f'Error: {str(e)}',
                'last_connection_test': fields.Datetime.now()
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Error',
                    'message': f'Error connecting to Odoo 14: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

