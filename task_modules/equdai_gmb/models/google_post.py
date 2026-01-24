# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class GooglePost(models.Model):
    _name = 'google.post'
    _description = 'Google Business Post'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    profile_id = fields.Many2one('google.business.profile', string='Location', required=True)
    summary = fields.Char(string='Summary/Title', required=True)
    content = fields.Text(string='Content', required=True)
    
    post_type = fields.Selection([
        ('STANDARD', 'What\'s New'),
        ('EVENT', 'Event'),
        ('OFFER', 'Offer'),
        ('ALERT', 'Alert (COVID-19/Status)')
    ], string='Type', default='STANDARD', required=True)
    
    # Event/Offer specific
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    
    # Offer specific
    coupon_code = fields.Char(string='Coupon Code')
    redemption_url = fields.Char(string='Redemption URL')
    
    # Action Button
    action_type = fields.Selection([
        ('BOOK', 'Book'),
        ('ORDER', 'Order Online'),
        ('SHOP', 'Shop'),
        ('LEARN_MORE', 'Learn More'),
        ('SIGN_UP', 'Sign Up'),
        ('CALL', 'Call')
    ], string='Call to Action')
    action_url = fields.Char(string='Action URL')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('failed', 'Failed')
    ], string='Status', default='draft')
    
    post_url = fields.Char(string='Post Link', readonly=True)
    
    # Analytics Fields
    views = fields.Integer(string='Views', default=0)
    click_count = fields.Integer(string='Clicks', default=0)

    def action_publish_post(self):
        self.ensure_one()
        token = self.profile_id.credentials_id.refresh_access_token()
        url = f"https://mybusiness.googleapis.com/v4/{self.profile_id.location_id}/localPosts"
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Build Payload
        payload = {
            'languageCode': 'en-US',
            'summary': self.summary,
            'topicType': self.post_type,
        }
        
        if self.post_type in ['EVENT', 'OFFER']:
             payload['event'] = {
                 'title': self.summary,
                 'schedule': {
                     'startDate': {'year': self.start_date.year, 'month': self.start_date.month, 'day': self.start_date.day},
                     'startTime': {'hours': self.start_date.hour, 'minutes': self.start_date.minute},
                     'endDate': {'year': self.end_date.year, 'month': self.end_date.month, 'day': self.end_date.day},
                     'endTime': {'hours': self.end_date.hour, 'minutes': self.end_date.minute},
                 }
             }
        
        if self.post_type == 'OFFER':
            payload['offer'] = {
                'couponCode': self.coupon_code,
                'redeemOnlineUrl': self.redemption_url,
                'termsConditions': self.content
            }
        
        if self.action_type:
            payload['callToAction'] = {
                'actionType': self.action_type,
                'url': self.action_url
            }

        # Note: 'media' handling would require uploading input stream to Google Media API first
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                self.write({
                    'state': 'posted',
                    'post_url': data.get('searchUrl')
                })
            else:
                self.write({'state': 'failed'})
                _logger.error("Failed to publish post: %s", response.text)
                raise UserError(_("Failed to publish: %s", response.text))
        except Exception as e:
            raise UserError(str(e))
