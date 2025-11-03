# -*- coding: utf-8 -*-
{
    'name': 'FM Inventory Custom',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'FM Inventory Customizations with Brand Management',
    'description': '''
        FM Inventory Custom Module
        ==========================
        
        This module extends Odoo Inventory to support:
        
        **Product Types:**
        - Uses Odoo's standard Product Type field: Goods, Service, and Consumable
        
        **Brand Management:**
        - Multiple brand variants per product
        - Brand-specific pricing
        - Brand-specific stock tracking per warehouse location
        - Brand selection at product line level in Sales/Purchase/Inventory
        
        **Features:**
        - Brand management menu under Inventory > Configuration
        - Brand-specific product views
        - Brand-specific inventory adjustments
        - Extended stock reports showing brand-wise quantities
        - Full integration with Sales, Purchase, and Inventory modules
        
        **Usage:**
        1. Configure brands under Inventory > Configuration > Brands
        2. Assign brands to products in Product form view
        3. Set brand-specific prices and stock levels
        4. Select brand when creating sales/purchase/inventory lines
    ''',
    'author': 'Equdai',
    'website': 'https://www.equdai.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
        'sale',
        'purchase',
        'fm_amc_crm_custom',  # Integration with previous CRM module
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/product_type_data.xml',
        'data/product_brand_demo.xml',
        'views/product_brand_views.xml',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'views/stock_quant_views.xml',
        'views/stock_move_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/inventory_menu_views.xml',
    ],
    'demo': [
        'data/product_brand_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Add CSS/JS if needed later
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}

