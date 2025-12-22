# -*- coding: utf-8 -*-
{
    'name': 'Partner Duplicate Merge',
    'version': '19.0.1.0.0',
    'category': 'CRM',
    'summary': 'Safe UI-based module to merge duplicate customers',
    'description': """
Partner Duplicate Merge
=======================
This module provides a safe UI-based interface to merge duplicate partners (customers).

Features:
---------
* Detect duplicate partners by name (case-insensitive)
* Select multiple partners to merge
* Choose primary (master) partner
* Merge all references correctly
* Archive merged partners (safe deletion)
* Log merge operations in chatter
    """,
    'author': 'Equinox',
    'depends': [
        'base',
        'crm',
        'sale',
        'purchase',
        'account',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/partner_merge_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

