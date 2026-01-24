# -*- coding: utf-8 -*-
{
    'name': "Equdai Social AI & Analytics",
    'summary': "AI Content Generation (OpenAI/Gemini) and Cross-Platform Analytics",
    'description': """
        - AI Assistant: Generate content using OpenAI or Google Gemini.
        - Analytics: Unified dashboard for GMB and Social Media performance.
    """,
    'author': "Equdai",
    'website': "https://equdai.ae",
    'category': 'Marketing',
    'version': '19.0.1.0.0',
    'depends': ['equdai_gmb', 'equdai_content_calendar', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'wizard/social_ai_generator_views.xml',
        'views/social_ai_views.xml',
        'views/unified_social_analytics_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
