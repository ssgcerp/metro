# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

class UnifiedContentCalendar(models.Model):
    _name = 'unified.content.calendar'
    _description = 'Unified Content Calendar'
    _auto = False
    _order = 'date_start desc'

    name = fields.Char(string='Content Title', readonly=True)
    date_start = fields.Datetime(string='Scheduled Date', readonly=True)
    date_stop = fields.Datetime(string='End Date', readonly=True)
    
    platform = fields.Char(string='Platform', readonly=True)
    state = fields.Char(string='Status', readonly=True)
    
    res_model = fields.Char(string='Model', readonly=True)
    res_id = fields.Integer(string='Record ID', readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW unified_content_calendar AS (
                SELECT
                    row_number() OVER () as id,
                    sub.name,
                    sub.date_start,
                    sub.date_stop,
                    sub.platform,
                    sub.state,
                    sub.res_model,
                    sub.res_id
                FROM (
                    -- Google Business Posts
                    SELECT
                        COALESCE(summary, 'GMB Post') as name,
                        COALESCE(start_date, create_date) as date_start,
                        COALESCE(end_date, start_date + interval '1 hour', create_date + interval '1 hour') as date_stop,
                        'Google Business' as platform,
                        state,
                        'google.post' as res_model,
                        id as res_id
                    FROM google_post

                    UNION ALL

                    -- Social Media Posts
                    SELECT
                        COALESCE(message, 'Social Post') as name,
                        COALESCE(scheduled_date, create_date) as date_start,
                        COALESCE(scheduled_date + interval '1 hour', create_date + interval '1 hour') as date_stop,
                        'Social' as platform,
                        state,
                        'social.post' as res_model,
                        id as res_id
                    FROM social_post
                ) sub
                WHERE sub.date_start IS NOT NULL
            )
        """)

    def action_open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
