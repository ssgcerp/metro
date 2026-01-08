# -*- coding: utf-8 -*-
{
    'name': 'AMC Contracts Management',
    'version': '19.0.1.0.6',
    'category': 'Sales',
    'summary': 'Annual Maintenance Contract (AMC) Management System',
    'description': '''
        AMC Contracts Management Module
        ===============================
        
        This module provides comprehensive management for Annual Maintenance Contracts (AMC) with:
        
        * Contract Lifecycle Management:
          - Draft, Confirmed, Cancelled, Blocked, Expired statuses
          - Dynamic status management with reordering capability
          - Default statuses that cannot be deleted but can be reordered
        
        * Flexible Contract Numbering:
          - Customizable contract number format
          - Supports prefix, branch code, sequential number, and year
          - Format: [PREFIX]/[BRANCH_CODE]/[SEQUENTIAL]/[YEAR]
          - Example: MFS/AMC/FUJ/1213/2025
        
        * Comprehensive Contract Information:
          - Customer and contact details
          - Project site information
          - Branch management
          - Sales contact assignment
          - Multiple tabs for organized information:
            * Types of Services
            * Registration Details
            * Invoice Schedule
            * Quotation Details
            * Service Schedules
            * Call Out
            * Additional Jobs
            * Terms and Condition
            * Agreement
            * Expenses
            * Other Info
        
        * Financial Tracking:
          - Contract value tracking
          - Labour and extra expenses
          - Automatic total calculation
          - Payment schedule management
        
        * Visit Management:
          - Number of visits tracking
          - Completion pending tracking
          - Visit scheduling
        
        * Document Management:
          - Header and stamp options
          - Agreement and terms management
    ''',
    'author': 'Equdai',
    'website': 'https://www.equdai.ae',
    'license': 'LGPL-3',
    'icon': '/amc_contracts/static/src/image/amc_icon.png',
    'depends': [
        'base',
        'sale',
        'purchase',
        'account',
        'contacts',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/amc_contract_config_data.xml',
        'data/amc_contract_stage_data.xml',
        'data/ir_sequence_data.xml',
        'views/res_company_views.xml',
        'views/amc_contract_config_views.xml',
        # Load stage views after contract views to ensure model fields are loaded
        'views/amc_contract_views.xml',
        'views/amc_contract_stage_views.xml',
        'views/amc_contract_type_of_service_views.xml',
        'views/amc_contract_registration_views.xml',
        'views/amc_contract_invoice_schedule_views.xml',
        'views/amc_contract_quotation_views.xml',
        'views/amc_contract_service_schedule_views.xml',
        'views/amc_contract_call_out_views.xml',
        'views/amc_contract_additional_job_views.xml',
        'views/amc_contract_agreement_views.xml',
        'views/amc_contract_expense_views.xml',
        'views/amc_contract_agreement_views.xml',
        'views/amc_contract_expense_views.xml',
        'views/amc_contract_asset_views.xml',
        'views/amc_contract_audit_schedule_views.xml',
        'views/amc_contract_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'amc_contracts/static/src/css/amc_contract_custom.css',
            'amc_contracts/static/src/js/amc_contract_badge_color.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}

