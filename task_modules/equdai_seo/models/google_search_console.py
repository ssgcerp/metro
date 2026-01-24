# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import datetime
import logging

_logger = logging.getLogger(__name__)

class GoogleSearchConsoleSite(models.Model):
    _name = 'google.search.console.site'
    _description = 'Search Console Site'

    name = fields.Char(string='Site URL', required=True)
    site_url = fields.Char(string='Site URL (API)', help="The identifier used by the API, e.g. sc-domain:example.com or https://example.com/")
    credentials_id = fields.Many2one('google.credentials', string='Credentials', required=True)
    report_ids = fields.One2many('google.search.console.report', 'site_id', string='Reports')
    
    def action_fetch_analytics_last_30_days(self):
        self.ensure_one()
        end_date = datetime.date.today() - datetime.timedelta(days=2) # Data is usually 2 days delayed
        start_date = end_date - datetime.timedelta(days=30)
        self.fetch_analytics(start_date, end_date)

    def fetch_analytics(self, start_date, end_date):
        self.ensure_one()
        token = self.credentials_id.refresh_access_token()
        site_id_encoded = requests.utils.quote(self.site_url)
        url = f"https://www.googleapis.com/webmasters/v3/sites/{site_id_encoded}/searchAnalytics/query"
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Dimensions: query (keyword) and date
        payload = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': ['query', 'date'],
            'rowLimit': 5000 
        }

        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            rows = data.get('rows', [])
            
            for row in rows:
                query = row['keys'][0]
                date_str = row['keys'][1]
                
                # Check duplication (naive approach, better to use SQL constraint or bulk upsert if volume is high)
                existing = self.env['google.search.console.report'].search([
                    ('site_id', '=', self.id),
                    ('query', '=', query),
                    ('date', '=', date_str)
                ], limit=1)
                
                vals = {
                    'site_id': self.id,
                    'date': date_str,
                    'query': query,
                    'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr': row.get('ctr', 0.0),
                    'position': row.get('position', 0.0),
                }
                
                if not existing:
                    self.env['google.search.console.report'].create(vals)
                else:
                    existing.write(vals)
        else:
            raise UserError(_("Failed to fetch analytics: %s", response.text))

class GoogleSearchConsoleReport(models.Model):
    _name = 'google.search.console.report'
    _description = 'GSC Performance Report'
    _order = 'date desc, clicks desc'

    site_id = fields.Many2one('google.search.console.site', string='Site',required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    query = fields.Char(string='Query/Keyword', required=True)
    
    clicks = fields.Integer(string='Clicks', group_operator='sum')
    impressions = fields.Integer(string='Impressions', group_operator='sum')
    ctr = fields.Float(string='CTR (%)', group_operator='avg', digits=(16, 2))
    position = fields.Float(string='Avg Position', group_operator='avg', digits=(16, 1))
