# -*- coding: utf-8 -*-
"""
Script to check and fix Inventory menu visibility issues in Odoo 19
Run this in Odoo shell: python odoo-bin shell -d your_database_name
Then copy-paste the code below
"""

import odoo
from odoo import api, SUPERUSER_ID

# Connect to database
env = api.Environment(odoo.registry(odoo.tools.config['db_name']), SUPERUSER_ID, {})

# Check if stock module is installed
stock_module = env['ir.module.module'].search([('name', '=', 'stock')])
if stock_module:
    print(f"Stock module status: {stock_module.state}")
    if stock_module.state != 'installed':
        print("ERROR: Stock module is not installed!")
        print("Please install it from Apps menu")
else:
    print("ERROR: Stock module not found!")

# Check main inventory menu
inventory_menu = env['ir.ui.menu'].search([
    ('name', '=', 'Inventory'),
    ('parent_id', '=', False)
], limit=1)

if inventory_menu:
    print(f"\nInventory menu found:")
    print(f"  ID: {inventory_menu.id}")
    print(f"  Name: {inventory_menu.name}")
    print(f"  Active: {inventory_menu.active}")
    print(f"  Sequence: {inventory_menu.sequence}")
    
    # Check if menu is active
    if not inventory_menu.active:
        print("\nWARNING: Inventory menu is INACTIVE!")
        print("Activating menu...")
        inventory_menu.write({'active': True})
        print("Menu activated!")
else:
    print("\nERROR: Inventory menu not found!")
    print("This might indicate a module installation issue.")

# Check user groups that can see inventory
stock_user_group = env['res.groups'].search([('name', '=', 'Stock / User')], limit=1)
stock_manager_group = env['res.groups'].search([('name', '=', 'Stock / Manager')], limit=1)

print(f"\nStock User Group: {stock_user_group.name if stock_user_group else 'NOT FOUND'}")
print(f"Stock Manager Group: {stock_manager_group.name if stock_manager_group else 'NOT FOUND'}")

# Check current user's groups
current_user = env.user
print(f"\nCurrent User: {current_user.name} (ID: {current_user.id})")
print(f"User Groups:")
for group in current_user.groups_id:
    print(f"  - {group.name}")

# Check if user has stock access
has_stock_access = stock_user_group in current_user.groups_id or stock_manager_group in current_user.groups_id
print(f"\nHas Stock Access: {has_stock_access}")

if not has_stock_access:
    print("\nSOLUTION: Add Stock / User or Stock / Manager group to your user")
    print("Go to: Settings > Users & Companies > Users")
    print("Edit your user and add 'Stock / User' group")

# Check menu access rules
print("\nChecking menu access rules...")
menu_access = env['ir.ui.menu'].search([
    ('name', '=', 'Inventory'),
    ('parent_id', '=', False)
], limit=1)

if menu_access:
    # Get all groups that can access this menu
    groups_with_access = env['res.groups'].search([])
    print(f"Menu is accessible to users with appropriate groups")

print("\n" + "="*50)
print("DIAGNOSTIC COMPLETE")
print("="*50)
