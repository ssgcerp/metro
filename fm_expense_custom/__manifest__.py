{
    'name': 'FM Expense Custom',
    'version': '1.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Customizations for Expenses',
    'description': """
        Adds Reference number field to expense form.
    """,
    'author': 'Antigravity',
    'depends': ['hr_expense', 'project', 'eq_fc_management'],
    'data': [
        'views/hr_expense_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
