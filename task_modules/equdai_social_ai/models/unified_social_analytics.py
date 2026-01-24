# -*- coding: utf-8 -*-

from odoo import models, fields, tools

class UnifiedSocialAnalytics(models.Model):
    _name = 'unified.social.analytics'
    _description = 'Unified Social Analytics'
    _auto = False

    date = fields.Date(string='Date', readonly=True)
    platform = fields.Selection([
        ('gmb', 'Google Business'), 
        ('social', 'Social Media')
    ], string='Platform', readonly=True)
    
    name = fields.Char(string='Post Name', readonly=True)
    
    impressions = fields.Integer(string='Impressions/Views', readonly=True)
    clicks = fields.Integer(string='Clicks', readonly=True)
    likes = fields.Integer(string='Likes', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW unified_social_analytics AS (
                SELECT
                    id as id,
                    create_date::date as date,
                    'gmb' as platform,
                    summary as name,
                    views as impressions,
                    click_count as clicks,
                    0 as likes
                FROM
                    google_post
                
                UNION ALL
                
                SELECT
                    id * 100000 as id,  -- Avoid ID collision
                    create_date::date as date,
                    'social' as platform,
                    message as name,
                    0 as impressions, -- social_post might not track this standardly across all types
                    0 as clicks,
                    0 as likes -- Placeholder if we don't know the exact column
                FROM
                    social_post
                WHERE exists (select 1 from information_schema.tables where table_name = 'social_post')
            )
        """)
