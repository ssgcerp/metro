# -*- coding: utf-8 -*-
{
    'name': "Equdai Unified Content Calendar",
    'summary': "Centralized Calendar for GMB and Social Media Posts",
    'description': """
        Visual Content Calendar aggregating:
        - Google Business Posts (from equdai_gmb)
        - Social Media Posts (from custom_task_template/social)
    """,
    'author': "Equdai",
    'website': "https://equdai.ae",
    'category': 'Marketing',
    'version': '19.0.1.0.0',
    'depends': ['equdai_gmb', 'custom_task_template'],
    'data': [
        'security/ir.model.access.csv',
        'views/unified_content_calendar_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
