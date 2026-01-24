# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import re
import time
import logging

_logger = logging.getLogger(__name__)

class SeoExternalAudit(models.Model):
    _name = 'seo.external.audit'
    _description = 'External Page SEO Audit'
    _order = 'scan_date desc'

    name = fields.Char(string='Page Name/URL', required=True)
    url = fields.Char(string='Target URL', required=True)
    target_keyword = fields.Char(string='Target Keyword')
    scan_date = fields.Datetime(string='Last Scan', readonly=True)
    
    # Results
    status_code = fields.Integer(string='Status Code', readonly=True)
    load_time = fields.Float(string='Load Time (s)', readonly=True)
    
    meta_title = fields.Char(string='Meta Title', readonly=True)
    meta_description = fields.Text(string='Meta Description', readonly=True)
    h1_tag = fields.Char(string='H1 Tag', readonly=True)
    
    score = fields.Integer(string='SEO Score', readonly=True)
    audit_notes = fields.Html(string='Detailed Report', readonly=True)

    def action_scan_page(self):
        self.ensure_one()
        if not self.url.startswith('http'):
            raise UserError(_("Please provide a valid URL starting with http:// or https://"))

        headers = {'User-Agent': 'Equdai-SEO-Bot/1.0'}
        start_time = time.time()
        
        try:
            response = requests.get(self.url, headers=headers, timeout=10)
            end_time = time.time()
            self.load_time = round(end_time - start_time, 2)
            self.status_code = response.status_code
            self.scan_date = fields.Datetime.now()
            
            if response.status_code == 200:
                self._analyze_html(response.text)
            else:
                self.score = 0
                self.audit_notes = f"<p class='text-danger'>Failed to load page. Status: {response.status_code}</p>"

        except Exception as e:
            self.score = 0
            self.audit_notes = f"<p class='text-danger'>Connection Error: {str(e)}</p>"

    def _analyze_html(self, html):
        score = 0
        notes = "<ul class='list-unstyled'>"
        
        # Helper regex extraction (simple, robust enough for basic tags)
        def get_tag_content(pattern, html):
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else False

        # 1. Title
        title = get_tag_content(r'<title>(.*?)</title>', html)
        self.meta_title = title or 'Missing'
        if title:
            if 30 <= len(title) <= 60:
                score += 25
                notes += "<li class='text-success'>✅ Title is optimized.</li>"
            else:
                score += 10
                notes += "<li class='text-warning'>⚠️ Title length should be between 30-60 chars.</li>"
        else:
            notes += "<li class='text-danger'>❌ Missing Meta Title.</li>"

        # 2. Description
        # Support both 'name' and 'property' (og)
        desc = get_tag_content(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html)
        self.meta_description = desc or 'Missing'
        if desc:
            if 120 <= len(desc) <= 160:
                score += 25
                notes += "<li class='text-success'>✅ Meta Description is optimized.</li>"
            else:
                score += 10
                notes += "<li class='text-warning'>⚠️ Meta Description length should be 120-160 chars.</li>"
        else:
            notes += "<li class='text-danger'>❌ Missing Meta Description.</li>"

        # 3. H1
        h1 = get_tag_content(r'<h1[^>]*>(.*?)</h1>', html)
        # cleanup tags inside h1
        if h1:
            h1 = re.sub(r'<[^>]+>', '', h1)
        
        self.h1_tag = h1 or 'Missing'
        if h1:
            score += 20
            notes += "<li class='text-success'>✅ H1 Tag present.</li>"
        else:
            notes += "<li class='text-danger'>❌ Missing H1 Tag.</li>"

        # 4. Keyword Check
        if self.target_keyword:
            kw_found = False
            if title and self.target_keyword.lower() in title.lower():
                notes += "<li class='text-success'>✅ Keyword found in Title.</li>"
                score += 10
                kw_found = True
            if h1 and self.target_keyword.lower() in h1.lower():
                 notes += "<li class='text-success'>✅ Keyword found in H1.</li>"
                 score += 10
                 kw_found = True
            
            if not kw_found:
                 notes += "<li class='text-warning'>⚠️ Keyword not found in Title or H1.</li>"
        else:
            score += 20 # Free points if no keyword specified
            notes += "<li class='text-muted'>ℹ️ No keyword specified for check.</li>"

        # 5. Performance
        if self.load_time < 1.0:
            score += 10
            notes += "<li class='text-success'>✅ Fast Load Time (< 1s).</li>"
        elif self.load_time < 2.5:
             score += 5
             notes += "<li class='text-warning'>⚠️ Moderate Load Time.</li>"
        else:
             notes += "<li class='text-danger'>❌ Slow Load Time (> 2.5s).</li>"

        notes += "</ul>"
        self.score = score
        self.audit_notes = notes
