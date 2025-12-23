# -*- coding: utf-8 -*-
{
    'name': 'EQ FC Invoice Custom',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom fields for Customer Invoices',
    'description': '''
        EQ FC Invoice Custom Module
        ===========================
        
        This module extends Customer Invoices (account.move) with custom fields:
        
        * Custom Fields:
          - Location
          - Site Name
          - Create DO (Delivery Order)
          - Bank Details
          - File Upload with filename
          - Invoice Note
          - AMC Contract (Selection field filtered by customer)
    ''',
    'author': 'Equdai',
    'website': 'https://www.equdai.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'amc_contracts',  # Required for AMC Contract field
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

