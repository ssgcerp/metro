# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import requests
import logging

_logger = logging.getLogger(__name__)

class GoogleBusinessProfile(models.Model):
    _name = 'google.business.profile'
    _description = 'Google Business Profile (Location)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Location Name', required=True, tracking=True)
    store_code = fields.Char(string='Store Code', tracking=True)
    google_place_id = fields.Char(string='Google Place ID', readonly=True)
    location_id = fields.Char(string='Google Location ID', required=True, readonly=True)
    
    address = fields.Text(string='Address')
    phone_number = fields.Char(string='Phone Number')
    website_url = fields.Char(string='Website')
    
    credentials_id = fields.Many2one('google.credentials', string='Credentials', required=True)
    
    average_rating = fields.Float(string='Average Rating', compute='_compute_rating_stats', store=True)
    review_count = fields.Integer(string='Review Count', compute='_compute_rating_stats', store=True)
    
    review_ids = fields.One2many('google.review', 'profile_id', string='Reviews')
    post_ids = fields.One2many('google.post', 'profile_id', string='Posts')
    service_ids = fields.One2many('google.service', 'profile_id', string='Services')

    @api.depends('review_ids.rating')
    def _compute_rating_stats(self):
        for profile in self:
            reviews = profile.review_ids
            profile.review_count = len(reviews)
            profile.average_rating = sum(reviews.mapped('rating')) / len(reviews) if reviews else 0.0

    def action_sync_location_details(self):
        """Sync details for this specific location"""
        self.ensure_one()
        token = self.credentials_id.refresh_access_token()
        url = f"https://mybusinessbusinessinformation.googleapis.com/v1/{self.location_id}"
        
        headers = {'Authorization': f'Bearer {token}'}
        params = {'readMask': 'title,storeCode,phoneNumbers,websiteUri,postalAddress'}
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            self.write({
                'name': data.get('title'),
                'store_code': data.get('storeCode'),
                'phone_number': data.get('phoneNumbers', {}).get('primaryPhone'),
                'website_url': data.get('websiteUri'),
                # Address parsing logic would go here
            })
        else:
            _logger.error("Failed to sync location: %s", response.text)

    @api.model
    def _cron_sync_locations(self):
        """Cron job to sync details for all profiles"""
        # Iterate over all profiles that have credentials
        profiles = self.search([('credentials_id', '!=', False)])
        for profile in profiles:
            try:
                profile.action_sync_location_details()
            except Exception as e:
                _logger.error("Cron sync failed for profile %s: %s", profile.name, str(e))

    def action_fetch_reviews(self):
        """Trigger review fetch for this location"""
        self.ensure_one()
        self.env['google.review'].fetch_reviews_for_location(self)
