# -*- coding: utf-8 -*-

{
    'name': 'PostgreSQL JSON Operator Fix',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Fix PostgreSQL 12 JSON operator compatibility issue',
    'description': """
        Fixes the PostgreSQL JSON operator error for varchar fields.
        Patches Odoo core _add_manual_models method to work with PostgreSQL 12.
    """,
    'author': 'EQ Development',
    'depends': ['base'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
