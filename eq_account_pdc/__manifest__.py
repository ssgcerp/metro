{
    'name': 'Account Pdc',
    'summary': """ Extension on Cheques to handle Post Dated Cheques """,
    'description': """ Extension on Cheques to handle Post Dated Cheques """,

    'author': 'Adevx',
    'category': 'Accounting/Accounting',
    "license": "OPL-1",
    'website': 'https://adevx.com',
    'version': '19.0.1.0.0',

    'depends': ['account_check_printing', 'sale', 'eq_cheque_management'],
    'data': [
        'views/account_payment.xml',
        'views/account_payment_register.xml',
        'views/sale_order.xml',
    ],

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}

