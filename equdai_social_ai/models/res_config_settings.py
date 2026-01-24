# -*- coding: utf-8 -*-

from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_provider = fields.Selection([
        ('openai', 'OpenAI (GPT-3.5/4)'),
        ('gemini', 'Google Gemini')
    ], string="AI Provider", config_parameter='equdai_social_ai.ai_provider', default='gemini')

    openai_api_key = fields.Char(string="OpenAI API Key", config_parameter='equdai_social_ai.openai_api_key')
    gemini_api_key = fields.Char(string="Gemini API Key", config_parameter='equdai_social_ai.gemini_api_key')
