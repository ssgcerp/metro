# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    google_post_ids = fields.Many2many('google.post', string='Linked GMB Posts')
    google_review_ids = fields.Many2many('google.review', string='Linked Reviews')
    
    google_post_count = fields.Integer(compute='_compute_gmb_counts')
    google_review_count = fields.Integer(compute='_compute_gmb_counts')
    
    @api.depends('google_post_ids', 'google_review_ids')
    def _compute_gmb_counts(self):
        for task in self:
            task.google_post_count = len(task.google_post_ids)
            task.google_review_count = len(task.google_review_ids)

    def action_view_google_posts(self):
        self.ensure_one()
        return {
            'name': 'Google Posts',
            'type': 'ir.actions.act_window',
            'res_model': 'google.post',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.google_post_ids.ids)],
            'context': {'default_profile_id': self.env['google.business.profile'].search([], limit=1).id}, # Heuristic default
        }

    def action_view_google_reviews(self):
        self.ensure_one()
        return {
            'name': 'Google Reviews',
            'type': 'ir.actions.act_window',
            'res_model': 'google.review',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.google_review_ids.ids)],
        }
