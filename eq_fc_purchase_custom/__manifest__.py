# -*- coding: utf-8 -*-
{
    'name': 'EQ FC Purchase Custom',
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'summary': 'RFQ Stages and Configuration for Purchase Orders',
    'description': '''
        EQ FC Purchase Custom Module
        ===========================
        
        This module extends Purchase Orders to provide:
        
        * RFQ Configuration:
          - Customizable RFQ number format
          - Supports prefix, branch code, sequential number, and year
          - Similar to AMC Estimation numbering system
        
        * RFQ Stages:
          - Custom workflow stages for RFQ
          - Status management for purchase orders
          - Stage-based workflow control
    ''',
    'author': 'Equdai',
    'website': 'https://www.equdai.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'purchase',
        'product',
        'stock',
        'project',
        'sale',
        'account',  # Required for account.move (vendor bills)
        'fm_inventory_custom',  # Required for product.brand model
        'eq_fc_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/eq_fc_rfq_config_data.xml',
        'data/eq_fc_rfq_stage_data.xml',
        'views/purchase_line_views.xml',
        'views/eq_fc_rfq_config_views.xml',
        'views/eq_fc_rfq_stage_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_menu_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

