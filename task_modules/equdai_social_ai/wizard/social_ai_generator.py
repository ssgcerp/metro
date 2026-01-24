# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class SocialAIGenerator(models.TransientModel):
    _name = 'social.ai.generator'
    _description = 'Social AI Content Generator'

    topic = fields.Char(string="Topic/Key Message", required=True)
    platform = fields.Selection([
        ('gmb', 'Google Business Profile'),
        ('linkedin', 'LinkedIn'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter/X'),
        ('facebook', 'Facebook')
    ], string="Platform", default='gmb', required=True)
    tone = fields.Selection([
        ('professional', 'Professional'),
        ('casual', 'Casual'),
        ('funny', 'Funny/Witty'),
        ('persuasive', 'Persuasive')
    ], string="Tone", default='professional', required=True)
    
    generated_content = fields.Text(string="Generated Content")

    def action_generate(self):
        self.ensure_one()
        provider = self.env['ir.config_parameter'].sudo().get_param('equdai_social_ai.ai_provider')
        if not provider:
            raise UserError(_("Please configure the AI Provider in Settings."))

        prompt = self._build_prompt()
        
        if provider == 'openai':
            content = self._generate_openai(prompt)
        elif provider == 'gemini':
            content = self._generate_gemini(prompt)
        else:
            raise UserError(_("Unknown AI Provider."))

        self.generated_content = content
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'social.ai.generator',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_use_content(self):
        """ Returns the content to the active record """
        self.ensure_one()
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        
        if active_model and active_id:
            record = self.env[active_model].browse(active_id)
            # Support both google.post (post_summary) and generic fields
            if hasattr(record, 'post_summary'):
                record.post_summary = self.generated_content
            elif hasattr(record, 'summary'):
                record.summary = self.generated_content
            elif hasattr(record, 'description'):
                record.description = self.generated_content
            elif hasattr(record, 'message'): # Generic social post
                record.message = self.generated_content
            
        return {'type': 'ir.actions.act_window_close'}

    def _build_prompt(self):
        return f"Write a {self.tone} social media post for {self.platform} about: '{self.topic}'. Include emojis and relevant hashtags."

    def _generate_openai(self, prompt):
        api_key = self.env['ir.config_parameter'].sudo().get_param('equdai_social_ai.openai_api_key')
        if not api_key:
            raise UserError(_("OpenAI API Key is missing."))
            
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7
        }
        try:
            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            raise UserError(_("OpenAI Error: %s", str(e)))

    def _generate_gemini(self, prompt):
        api_key = self.env['ir.config_parameter'].sudo().get_param('equdai_social_ai.gemini_api_key')
        if not api_key:
            raise UserError(_("Gemini API Key is missing."))
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            'contents': [{'parts': [{'text': prompt}]}]
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            # Handle Gemini response structure
            try:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return text
            except (KeyError, IndexError):
                return _("No content returned from Gemini.")
        except Exception as e:
            raise UserError(_("Gemini Error: %s", str(e)))
