# -*- coding: utf-8 -*-
{
    'name': 'Project Dashboard Module',
    'version': '19.0.1.0.0',
    'category': 'Project',
    'summary': 'Comprehensive project dashboard with multiple tabs and detailed views',
    'description': """
Project Dashboard Module
========================
This module provides a comprehensive project dashboard with:
- List view of all projects
- Detailed project dashboard with multiple tabs:
  * Project Summary
  * Estimation Sales Lines (with Product Reference, Brand, Description, Quantity, Unit)
  * Description
  * Consumables
  * Delivery Indents
  * Inventory Return
  * Cheque Details
  * Settings
- Full CRUD operations on dashboard data
- Easy navigation and editing capabilities
    """,
    'author': 'Equdai',
    'website': 'https://www.equdai.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'project',
        'sale_management',
        'product',
        'stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/project_dashboard_views.xml',
        'views/project_dashboard_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
