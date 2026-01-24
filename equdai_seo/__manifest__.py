# -*- coding: utf-8 -*-
{
    'name': "Equdai SEO & Search Console",
    'summary': "Google Search Console Integration and Rank Tracking",
    'description': """
        Track your website's organic performance directly in Odoo:
        - Sites: Manage multiple Search Console properties.
        - Reports: Fetch Clicks, Impressions, CTR, and Average Position (Rank) by Query/Keyword.
        - Dashboard: Performance analysis over time.
    """,
    'author': "Equdai",
    'website': "https://equdai.ae",
    'category': 'Marketing',
    'version': '19.0.1.0.0',
    'depends': ['equdai_gmb'],
    'data': [
        'security/ir.model.access.csv',
        'views/seo_views.xml',
        'views/seo_external_audit_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
