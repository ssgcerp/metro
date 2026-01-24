# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)

class GoogleReview(models.Model):
    _name = 'google.review'
    _description = 'Google Review'
    _order = 'create_time desc'

    review_id = fields.Char(string='Review ID', required=True, readonly=True)
    profile_id = fields.Many2one('google.business.profile', string='Location', required=True, ondelete='cascade')
    
    reviewer_name = fields.Char(string='Reviewer Name')
    reviewer_profile_photo_url = fields.Char(string='Reviewer Photo')
    
    rating = fields.Selection([
        ('ONE', '1 Star'),
        ('TWO', '2 Stars'),
        ('THREE', '3 Stars'),
        ('FOUR', '4 Stars'),
        ('FIVE', '5 Stars')
    ], string='Rating', required=True)
    
    numeric_rating = fields.Integer(string='Numeric Rating', compute='_compute_numeric_rating', store=True)

    comment = fields.Text(string='Review Comment')
    create_time = fields.Datetime(string='Created Time')
    
    reply_comment = fields.Text(string='My Reply')
    reply_time = fields.Datetime(string='Replied Time')
    is_replied = fields.Boolean(string='Replied', default=False)

    @api.depends('rating')
    def _compute_numeric_rating(self):
        mapping = {'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5}
        for review in self:
            review.numeric_rating = mapping.get(review.rating, 0)

    @api.model
    def _cron_fetch_reviews(self):
        """Cron job to fetch reviews for all profiles"""
        profiles = self.env['google.business.profile'].search([('credentials_id', '!=', False)])
        for profile in profiles:
            try:
                self.fetch_reviews_for_location(profile)
            except Exception as e:
                _logger.error("Cron review fetch failed for profile %s: %s", profile.name, str(e))

    @api.model
    def fetch_reviews_for_location(self, profile):
        """Fetch reviews for a specific location"""
        token = profile.credentials_id.refresh_access_token()
        # Note: Construct the correct resource name for the v4 or v1 API
        # Since v1 API for reviews is "accounts/{accountId}/locations/{locationId}/reviews"
        # We assume location_id has the full resource name or build it
        resource_name = profile.location_id 
        url = f"https://mybusinessreviews.googleapis.com/v1/{resource_name}/reviews"
        
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            reviews_data = response.json().get('reviews', [])
            for r in reviews_data:
                existing = self.search([('review_id', '=', r['reviewId'])], limit=1)
                vals = {
                    'profile_id': profile.id,
                    'review_id': r['reviewId'],
                    'reviewer_name': r.get('reviewer', {}).get('displayName'),
                    'reviewer_profile_photo_url': r.get('reviewer', {}).get('profilePhotoUrl'),
                    'rating': r.get('starRating'),
                    'comment': r.get('comment'),
                    # 'create_time': r.get('createTime'), # Needs parsing
                }
                
                # Check for existing reply
                if 'reviewReply' in r:
                    vals['reply_comment'] = r['reviewReply'].get('comment')
                    vals['is_replied'] = True
                    
                if not existing:
                    self.create(vals)
                else:
                    existing.write(vals)

    def action_post_reply(self):
        """Post a reply to the review"""
        self.ensure_one()
        if not self.reply_comment:
            raise UserError(_("Please write a reply first."))

        token = self.profile_id.credentials_id.refresh_access_token()
        url = f"https://mybusinessreviews.googleapis.com/v1/{self.profile_id.location_id}/reviews/{self.review_id}/reply"
        
        headers = {'Authorization': f'Bearer {token}'}
        data = {'comment': self.reply_comment}
        
        response = requests.put(url, headers=headers, json=data)
        if response.status_code == 200:
            self.is_replied = True
            self.reply_time = fields.Datetime.now()
        else:
            raise UserError(_("Failed to post reply: %s", response.text))
