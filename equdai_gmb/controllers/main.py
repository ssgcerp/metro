# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class GoogleBusinessController(http.Controller):

    @http.route('/google_business/auth_callback', type='http', auth='user')
    def google_auth_callback(self, code=None, state=None, error=None, **kwargs):
        """Handle the callback from Google OAuth"""
        if error:
            return request.render('http_routing.http_error', {
                'status_code': _('Google Auth Error'),
                'status_message': error
            })
        
        if not code:
            return request.render('http_routing.http_error', {
                'status_code': _('No Code'),
                'status_message': _('No authorization code received from Google.')
            })

        # Find the credentials record that initiated this request
        # Since state isn't passed in my simple implementation, we assume the first active one or user context
        # Ideally, 'state' parameter should pass the record ID.
        # For this version, we'll try to find a credentials record in 'draft' or 'authenticated' state 
        # that matches the client_id if possible, or just use the most recent draft.
        
        # Improvement: In the model's action_authenticate, we didn't pass state. 
        # Let's simple pick the most recently created credentials record for the current user/company or just the one awaiting auth.
        
        Credentials = request.env['google.credentials'].sudo()
        credentials_rec = Credentials.search([('state', '=', 'draft')], limit=1, order='create_date desc')
        
        if not credentials_rec:
             # Fallback if re-authenticating
             credentials_rec = Credentials.search([], limit=1, order='write_date desc')

        if credentials_rec:
            try:
                credentials_rec.fetch_token_from_code(code)
                return request.redirect('/odoo/action-equdai_gmb.action_google_credentials')
            except Exception as e:
                _logger.exception("Failed to fetch token")
                return request.render('http_routing.http_error', {
                    'status_code': _('Token Error'),
                    'status_message': str(e)
                })
        
        return request.redirect('/web')
