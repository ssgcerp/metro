# -*- coding: utf-8 -*-
{
    'name': 'EQ Project Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Project',
    'summary': 'Rich project dashboard with KPIs, charts, and navigation tabs',
    'description': """
EQ Project Dashboard
====================
Adds a comprehensive dashboard button to projects with:
- Real-time KPIs (Invoices, Costs, Profits)
- Interactive charts (Pie and Bar charts)
- Navigation tabs to Estimates, Invoices, Expenses, Purchases, Timesheets, Warehouse
- Modern, attractive UI with responsive design
    """,
    'author': 'EQ Development',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'project',
        'sale_management',
        'account',
        'purchase',
        'hr_expense',
        'stock',
        'analytic',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/project_dashboard_view.xml',
        # Note: dashboard_templates.xml removed - using OWL templates in JavaScript instead
        # Note: project_form_dashboard_button.xml is commented out until correct form view ID is found
        # To add the button: Find the form view external ID in Settings > Technical > Views
        # Then uncomment the line below and update the inherit_id in project_form_dashboard_button.xml
        # 'views/project_form_dashboard_button.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'eq_project_dashboard/static/src/js/project_dashboard.js',
            'eq_project_dashboard/static/src/js/project_form_button.js',
            'eq_project_dashboard/static/src/scss/dashboard_style.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}

