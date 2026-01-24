# -*- coding: utf-8 -*-
{
    'name': 'Quotation Revision',
    'version': "19.0.1",
    'description': """Revisions and Versions for Sales Orders and Quotations""",
    'author': "Odox Softhub",
    'depends': ['base', 'sale'],
    'data': [
        'security/eq_saleorder_revision_security.xml',
        'security/ir.model.access.csv',
        'views/noupdate.xml',
        'views/sales.xml',
        'wizards/revision_wizard.xml'
    ],
    'installable': True,
    'application': True,
}
