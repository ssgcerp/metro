{
    'name': 'Partner Statement of Account (SOA)',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Reporting',
    'summary': 'Generate professional Customer and Vendor Statements of Account',
    'description': """
        Partner Statement of Account (SOA) Module
        =========================================
        This module allows you to generate and send professional partner statements.

        Features:
        - Activity Statement (inc. Opening Balance)
        - Outstanding Statement
        - Aging Report
        - PDF & XLSX Reports
        - Automated Monthly Emails
        - Portal Access
    """,
    'author': 'Antigravity',
    'website': 'https://www.example.com',
    'depends': ['account', 'mail', 'portal', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/mail_template_data.xml',
        'views/menu_items.xml',
        'data/report_dynamic_data.xml',
        'views/res_config_settings_view.xml',
        'views/partner_statement_wizard_view.xml',
        'views/res_partner_view.xml',
        'views/portal_templates.xml',
        'report/report_partner_statement.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
