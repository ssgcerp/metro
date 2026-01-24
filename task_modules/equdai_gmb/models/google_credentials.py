# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import urllib.parse

class GoogleCredentials(models.Model):
    _name = 'google.credentials'
    _description = 'Google API Credentials'

    name = fields.Char(string='Name', required=True)
    client_id = fields.Char(string='Client ID', required=True)
    client_secret = fields.Char(string='Client Secret', required=True)
    redirect_uri = fields.Char(string='Redirect URI', default=lambda self: self._get_default_redirect_uri(), required=True)
    
    authorization_code = fields.Char(string='Authorization Code', readonly=True)
    refresh_token = fields.Char(string='Refresh Token', readonly=True)
    access_token = fields.Char(string='Access Token', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('authenticated', 'Authenticated')
    ], string='Status', default='draft')

    def _get_default_redirect_uri(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/google_business/auth_callback"

    def action_authenticate(self):
        self.ensure_one()
        if not self.client_id or not self.redirect_uri:
            raise UserError(_("Please configure Client ID and Redirect URI."))

        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        scope = " ".join([
            "https://www.googleapis.com/auth/business.manage",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/webmasters.readonly"
        ])
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': scope,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        auth_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'self',
        }

    def fetch_token_from_code(self, code):
        """Exchange auth code for tokens"""
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            tokens = response.json()
            self.write({
                'authorization_code': code,
                'refresh_token': tokens.get('refresh_token'),
                'access_token': tokens.get('access_token'),
                'state': 'authenticated'
            })
            return True
        else:
            raise UserError(_("Failed to fetch token: %s", response.text))

    def refresh_access_token(self):
        """Refresh the access token using the refresh token"""
        self.ensure_one()
        if not self.refresh_token:
            raise UserError(_("No refresh token available. Re-authenticate."))

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            tokens = response.json()
            self.write({
                'access_token': tokens.get('access_token')
            })
            return tokens.get('access_token')
        else:
            # If refresh fails, might need re-auth
            raise UserError(_("Failed to refresh token: %s", response.text))
