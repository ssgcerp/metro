# -*- coding: utf-8 -*-

from odoo import models, fields, api

class WebsitePage(models.Model):
    _inherit = 'website.page'

    seo_score = fields.Integer(string='SEO Score', compute='_compute_seo_score', store=True)
    seo_notes = fields.Html(string='SEO Audit Notes', compute='_compute_seo_score')

    @api.depends('website_meta_title', 'website_meta_description', 'url', 'is_published', 'website_indexed')
    def _compute_seo_score(self):
        for page in self:
            score = 0
            notes = "<ul>"
            
            # 1. Meta Title Check
            if page.website_meta_title:
                score += 30
                if len(page.website_meta_title) > 60:
                     notes += "<li class='text-warning'>Title is too long (> 60 chars).</li>"
                else:
                     notes += "<li class='text-success'>Title is optimized.</li>"
            else:
                notes += "<li class='text-danger'>Missing Meta Title.</li>"

            # 2. Meta Description Check
            if page.website_meta_description:
                score += 30
                if len(page.website_meta_description) < 50:
                    notes += "<li class='text-warning'>Description is too short.</li>"
                elif len(page.website_meta_description) > 160:
                     notes += "<li class='text-warning'>Description is too long (> 160 chars).</li>"
                else:
                     notes += "<li class='text-success'>Description is optimized.</li>"
            else:
                notes += "<li class='text-danger'>Missing Meta Description.</li>"

            # 3. URL Check
            if page.url and len(page.url) < 80:
                score += 20
                notes += "<li class='text-success'>URL length is good.</li>"
            else:
                notes += "<li class='text-warning'>URL is quite long.</li>"

            # 4. Indexing Check
            if page.is_published and page.website_indexed:
                score += 20
                notes += "<li class='text-success'>Page is Published & Indexed.</li>"
            else:
                notes += "<li class='text-danger'>Page is unpublished or noindex.</li>"

            notes += "</ul>"
            page.seo_score = score
            page.seo_notes = notes
