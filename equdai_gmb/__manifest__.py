# -*- coding: utf-8 -*-
{
    'name': "Equdai Google Business Management",
    'summary': """
        Manage Google Business Profiles, Reviews, Posts, and Services.
        Integrates with Odoo Projects.
    """,
    'description': """
        Comprehensive Google Business Management module:
        - Manage multiple Google Business Credentials
        - Sync and manage Business Profiles (Locations)
        - Read and Reply to Reviews
        - Publish Posts (Events, Offers, Updates)
        - Manage Services
        - Integrate GMB activities with Odoo Project Tasks
    """,
    'author': "Equdai",
    'website': "https://equdai.ae",
    'category': 'Marketing',
    'version': '19.0.1.0.0',
    'depends': ['base', 'mail', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/google_credentials_views.xml',
        'views/google_review_views.xml',
        'views/google_business_profile_views.xml',
        'views/google_post_views.xml',
        'views/google_service_views.xml',
        'views/project_task_views.xml',
        'views/google_menu_views.xml',
        'data/ir_cron_data.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
