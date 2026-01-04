# -*- coding: utf-8 -*-
{
    'name': 'Equdai Cheque Management',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Comprehensive Cheque Management System with PDC/CDC Support',
    'description': '''
        Equdai Cheque Management Module
        ================================
        
        A comprehensive cheque lifecycle management system supporting:
        
        * Incoming & Outgoing Cheques
        * CDC (Current Date Cheque) & PDC (Post Dated Cheque) Support
        * Full Accounting Integration with Journal Entries
        * UAE/GCC Compliant Chart of Accounts
        * Queue-based Auto-Deposit for PDC Cheques
        * AMC/Contract Integration
        * Complete Workflow Management (Draft → Registered → Deposited → Done)
        * Bounce & Return Handling with Accounting Reversal
        * Enterprise-level UI with Smart Buttons & Status Bars
        * Multi-company Safe & Fully Uninstallable
    ''',
    'author': 'Equdai',
    'website': 'https://www.equdai.ae',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'account_accountant',
        'base',
        'mail',
        'queue_job',
        'amc_contracts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        'security/security.xml',
        'data/ir_sequence_data.xml',
        'data/account_payment_method_data.xml',
        'data/ir_cron_data.xml',
        'views/bank_cheque_views.xml',
        'views/cheque_book_views.xml',
        'wizard/cheque_print_views.xml',
        'views/eq_cheque_config_views.xml',
        'views/res_company_views.xml',
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
        'views/eq_cheque_incoming_views.xml',
        'views/eq_cheque_outgoing_views.xml',
        'views/amc_contract_views.xml',
        'views/eq_cheque_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}

