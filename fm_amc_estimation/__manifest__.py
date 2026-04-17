# -*- coding: utf-8 -*-
{
    'name': 'FM AMC Estimation',
    'version': '19.0.1.0.56',
    'category': 'Estimation',
    'summary': 'Estimation Management for AMC Contracts and Projects',
    'description': '''
        FM AMC Estimation Module
        ========================
        
        This module extends CRM and integrates with AMC Contracts to provide:
        
        * Estimation Management:
          - Separate estimation workflow from standard CRM quotations
          - Designed for projects and AMC contracts
          - Status workflow: Draft, Waiting Approval, Approved, Locked
        
        * Integration:
          - Link estimations to AMC Contracts
          - Link estimations to Projects
          - Convert approved estimations to standard CRM quotations
        
        * Estimation Lines:
          - Project estimations
          - Consumable estimations
          - Complete item tracking and pricing
        
        * Number Format Configuration:
          - Customizable estimation number format
          - Similar to AMC Contracts numbering system
          - Supports prefix, branch code, sequential number, and year
        
        * Status Management:
          - Draft: Initial state, can be modified
          - Waiting Approval: Submitted for approval
          - Approved: Approved and ready for quotation creation
          - Locked: Final state, cannot be modified
    ''',
    'author': 'Equdai',
    'website': 'https://www.equdai.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sales_team',
        'sale',
        'crm',
        'project',
        'amc_contracts',
        'product',
        'stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/fm_amc_estimation_stage_data.xml',
        'data/fm_amc_estimation_config_data.xml',
        'data/fm_amc_quotation_stage_data.xml',
        'data/fm_amc_quotation_config_data.xml',
        'data/fm_amc_product_sku_config_data.xml',
        'data/fm_amc_quotation_sequence_data.xml',
        'data/amc_quotation_sequence_data.xml',
        'views/product_views.xml',
        'views/fm_amc_product_sku_config_views.xml',
        'views/fm_amc_estimation_config_views.xml',
        'views/fm_amc_estimation_stage_views.xml',
        'views/fm_amc_quotation_config_views.xml',
        'views/fm_amc_quotation_stage_views.xml',
        'views/fm_amc_estimation_views.xml',
        'views/fm_amc_estimation_line_views.xml',
        'views/fm_amc_terms_condition_views.xml',
        'views/fm_amc_system_type_views.xml',
        'views/fm_amc_contract_period_views.xml',
        'views/amc_quotation_views.xml',
        'views/crm_menu_views.xml',
        'views/estimation_menu_views.xml',
        'views/amc_contract_inherit_views.xml',
        'views/sale_order_amc_inherit_views.xml',
        'views/account_move_inherit_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fm_amc_estimation/static/src/css/fm_amc_estimation_custom.css',
            'fm_amc_estimation/static/src/js/fm_amc_estimation_menu.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}


