# Project Dashboard Module

## Overview
This module provides a comprehensive project dashboard for Odoo 19 with multiple tabs for managing project-related data.

## Features

### Main Dashboard
- List view of all projects
- Detailed project form view with multiple tabs
- Easy navigation and editing capabilities

### Dashboard Tabs

1. **Project Summary**
   - Basic project information
   - AMC project indicator
   - Project manager and customer details

2. **Estimation Sales Lines**
   - Product table with columns:
     - Product Reference (from product.default_code)
     - Brand (from product.brand_id)
     - Description
     - Quantity
     - Unit (UOM)
   - Inline editing support
   - Add/Edit/Delete capabilities

3. **Description**
   - Rich text HTML editor for project description

4. **Consumables**
   - List of consumable items
   - Product, description, quantity, and unit

5. **Delivery Indents**
   - Track delivery indents
   - Status workflow: Draft → Confirmed → Delivered → Cancelled

6. **Inventory Return**
   - Track inventory returns
   - Status workflow: Draft → Confirmed → Returned → Cancelled

7. **Cheque Details**
   - Manage cheque information
   - Status workflow: Draft → Issued → Cleared/Bounced → Cancelled

8. **Settings**
   - Project configuration options
   - Privacy settings
   - Date ranges

## Installation

1. Copy the module to your Odoo addons directory
2. Update the app list in Odoo
3. Install "Project Dashboard Module"

## Dependencies

- base
- project
- sale_management
- product
- stock
- account

## Usage

1. Navigate to **Project > Project Dashboard** from the main menu
2. Click on any project to view its detailed dashboard
3. Use the tabs to navigate between different sections
4. Add, edit, or delete entries directly from the dashboard

## Models

- `project.project` (extended)
- `project.estimation.sales.line`
- `project.consumable.line`
- `project.delivery.indent`
- `project.inventory.return`
- `project.cheque.detail`

## Technical Notes

- All models have proper security rules
- Inline editing is supported for estimation sales lines and consumables
- Product reference and brand are automatically populated from the selected product
- All fields are properly indexed for performance

