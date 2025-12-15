# -*- coding: utf-8 -*-
{
    'name': 'Odoo 14 to Odoo 19 Invoice & Purchase Migration',
    'version': '19.0.1.0.3',
    'category': 'Migration',
    'summary': 'Migrate invoices and purchase invoices from Odoo 14 to Odoo 19',
    'description': """
Odoo 14 to Odoo 19 Migration Module
===================================
This module allows you to migrate invoices and purchase invoices from an Odoo 14 instance to Odoo 19.

Features:
---------
* Connect to Odoo 14 instance via XML-RPC API
* Test connection before migration
* Select which documents to migrate (customers, quotations, employees, invoices, purchase invoices)
* Preview data count before migration
* Progress tracking during migration
* Error handling and logging
* Migration summary report
    """,
    'author': 'EQ Development',
    'website': 'https://www.equdai.ae',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'purchase',
        'product',
        'base',
        'web',
        'hr',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'security/employee_preview_security.xml',
        'views/migration_config_views.xml',
        'views/migration_item_views.xml',
        'views/migration_wizard_views.xml',
        'views/customer_migration_wizard_views.xml',
        'views/employee_migration_wizard_views.xml',
        'views/customer_preview_views.xml',
        'views/employee_preview_views.xml',
        'views/quotation_preview_views.xml',
        'views/invoice_preview_views.xml',
        'views/menu_items.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo14_to_19_migration/static/src/js/test_assets.js',
            'odoo14_to_19_migration/static/src/js/migration_auto_continue.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}

