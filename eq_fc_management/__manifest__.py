# -*- coding: utf-8 -*-
{
    'name': 'Equdai Project Financial Control',
    'version': '19.0.1.0.0',
    'category': 'Project',
    'summary': 'Project Financial Control Management with Configuration',
    'description': '''
        This module provides:
        - Project Configuration page for setting up project numbering formats
        - Automatic project code generation on project confirmation
        - Project financial tracking with actual vs estimated costs
        - Profit and invoice payment tracking
        - Visual indicators for cost overruns and profit thresholds
        - Branch details management
    ''',
    'author': 'Equdai',
    'website': 'https://www.equdai.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'project',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        'views/fc_project_config_views.xml',
        'views/fc_project_stage_views.xml',
        'views/fc_project_views.xml',
        'views/fc_project_menus.xml',
        'data/fc_project_config_data.xml',
        'data/fc_project_stage_data.xml',
        'data/fc_project_migration.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'eq_fc_management/static/src/css/fc_project_custom.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
