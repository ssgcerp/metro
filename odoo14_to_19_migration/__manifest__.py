# -*- coding: utf-8 -*-
{
    'name': 'Odoo 14 to Odoo 19 Invoice & Purchase Migration',
    'version': '19.0.1.0.0',
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
* Select which documents to migrate (invoices, purchase invoices)
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
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
                    'data': [
                        'security/ir.model.access.csv',
                        'views/migration_config_views.xml',
                        'views/migration_item_views.xml',
                        'views/migration_wizard_views.xml',
                        'views/customer_migration_wizard_views.xml',
                        'views/customer_preview_views.xml',
                        'views/quotation_preview_views.xml',
                        'views/invoice_preview_views.xml',
                        'views/menu_items.xml',
                    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

