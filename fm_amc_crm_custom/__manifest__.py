# -*- coding: utf-8 -*-
{
    'name': 'FM AMC CRM Custom',
    'version': '19.0.1.0.80',
    'category': 'Sales/CRM',
    'summary': 'FM AMC CRM Customizations',
    'description': '''
        FM AMC CRM Custom Module
        ========================
        Customizations for FM AMC CRM and Sale workflow:
        - Custom quotation stages and workflow
        - Estimation integration with quotations
        - Quotation approval process
        - Estimated values and pricing
    ''',
    'author': 'Equdai',
    'website': 'https://www.equdai.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'crm',
        'sale_management',
        'fm_amc_estimation',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sale_quotation_stage_data.xml',
        'data/sale_quotation_config_data.xml',
        'views/sale_quotation_decline_wizard_views.xml',
        'views/crm_menu_views.xml',
        'views/sale_quotation_config_views.xml',
        'views/sale_quotation_stage_views.xml',
        'views/sale_order_extended_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
