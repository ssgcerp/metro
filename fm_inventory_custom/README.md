# FM Inventory Custom Module

## Overview

The **FM Inventory Custom** module extends Odoo 19 Inventory functionality with brand management and additional product types. This module is compatible with both Community and Enterprise editions.

## Features

### 1. Product Types

The module uses Odoo's standard Product Type field with three options:
- **Goods** (product): Storable products tracked in inventory
- **Service** (service): Services that are not tracked in inventory
- **Consumable** (consu): Products that are consumed but not tracked in inventory

### 2. Brand Management System

- **Multiple Brand Variants**: Each product can have multiple brand variants
- **Brand-Specific Pricing**: Set individual prices for each brand variant
- **Brand-Specific Stock Tracking**: Track stock per brand variant and warehouse location
- **Brand Selection in Lines**: Select brand variants when creating Sales, Purchase, and Inventory lines

### 3. Integration Points

- **Sales Orders**: Brand variant selection in sale order lines
- **Purchase Orders**: Brand variant selection in purchase order lines
- **Inventory**: Brand-aware stock tracking and moves
- **Stock Reports**: Extended to show brand-wise quantities

## Installation

1. Copy the `fm_inventory_custom` folder to your Odoo addons directory
2. Update the Apps list: **Apps** → **Update Apps List**
3. Install the module: **Apps** → Search "FM Inventory Custom" → **Install**

## Usage Guide

### Setting Up Brands

1. Navigate to **Inventory** → **Configuration** → **Brands**
2. Click **Create** to add a new brand
3. Fill in:
   - **Brand Name**: Name of the brand (e.g., "Premium Brands")
   - **Brand Code**: Short code (e.g., "PRM")
   - **Logo**: Upload brand logo (optional)
   - **Description**: Brand description (optional)

### Assigning Brands to Products

1. Open a product from **Inventory** → **Products** → **Products**
2. In the product form, set the **Brand** field (primary brand)
3. Go to the **Brand Variants** tab
4. Click **Add a line** to create brand variants
5. For each variant:
   - Select **Brand**
   - Set **Sales Price** (brand-specific)
   - Configure **Location Stock** as needed

### Managing Brand-Specific Stock

1. In the product form, open the **Brand Variants** tab
2. Select a brand variant
3. Click **Stock Locations** button
4. Add stock records for each location:
   - Select **Location**
   - Set **Quantity**
   - Set **Reserved Quantity** if needed
5. The **Available Quantity** is automatically calculated

### Using Brands in Sales Orders

1. Create or edit a **Sale Order**
2. Add a product line
3. Select the **Brand Variant** from the dropdown
4. The price will automatically update if a brand-specific price is set
5. The product description will include the brand name

### Using Brands in Purchase Orders

1. Create or edit a **Purchase Order**
2. Add a product line
3. Select the **Brand Variant** from the dropdown
4. The product description will include the brand name

### Using Brands in Inventory

1. When viewing **Inventory** → **Products** → **Stock On Hand**, brand variants are shown
2. When creating stock moves, brand variants can be selected
3. Stock adjustments respect brand variants

## Module Structure

```
fm_inventory_custom/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── product_brand.py           # Brand model
│   ├── product_template.py        # Product template extensions
│   ├── product_product.py          # Product product extensions
│   ├── stock_quant.py              # Stock quant extensions
│   ├── stock_move.py               # Stock move extensions
│   ├── sale_order_line.py          # Sale order line extensions
│   └── purchase_order_line.py      # Purchase order line extensions
├── views/
│   ├── product_brand_views.xml
│   ├── product_template_views.xml
│   ├── sale_order_views.xml
│   ├── purchase_order_views.xml
│   ├── stock_quant_views.xml
│   ├── stock_move_views.xml
│   └── inventory_menu_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── data/
│   ├── product_type_data.xml
│   └── product_brand_demo.xml
└── static/
    └── description/
        └── (banner.png - optional)
```

## Models

### product.brand
Main brand model with name, code, logo, and description.

### product.brand.variant
Brand variants for products with brand-specific pricing and stock tracking.

### product.brand.stock
Stock tracking per brand variant and warehouse location.

## Security

- **Inventory Manager**: Full access to brand management
- **Inventory User**: Read access to brands, can create brand variants and stock records

## Demo Data

The module includes demo data with 3 sample brands:
- Premium Brands (PRM)
- Standard Brands (STD)
- Economy Brands (ECO)

## Technical Notes

- Brand variants are linked to product templates (not individual product variants)
- Stock tracking uses a custom model (`product.brand.stock`) alongside standard Odoo stock quants
- Brand selection automatically updates prices and descriptions in sales/purchase lines
- All terms are translatable

## Troubleshooting

### Brand variant not showing in dropdown
- Ensure the brand variant is created in the product's Brand Variants tab
- Check that the brand variant is active

### Stock not updating
- Brand-specific stock is tracked separately from standard Odoo stock quants
- Use the Stock Locations button in brand variants to manage brand-specific stock

### Price not updating
- Ensure brand-specific price is set in the brand variant
- Check that the brand variant is selected in the order line

## Support

For issues or questions, contact your system administrator or refer to the module documentation.

## Version History

- **19.0.1.0.0**: Initial release with brand management and custom product types

