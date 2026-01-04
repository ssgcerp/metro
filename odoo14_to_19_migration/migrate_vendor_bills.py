#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vendor Bill Migration Helper Script
This script provides command-line utilities for vendor bill migration
"""

import sys
import os
import argparse
from datetime import datetime

# Add Odoo to path if needed
try:
    import odoo
    from odoo import api, SUPERUSER_ID
except ImportError:
    print("Error: Odoo not found. Please run this script from Odoo environment.")
    sys.exit(1)


def get_env(database_name):
    """Get Odoo environment"""
    try:
        odoo.tools.config.parse_config(['-d', database_name])
        registry = odoo.registry(database_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            return env
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)


def check_modules(env):
    """Check if required modules are installed"""
    print("\n" + "="*50)
    print("Checking Required Modules")
    print("="*50)
    
    required_modules = [
        'odoo14_to_19_migration',
        'eq_fc_purchase_custom',
        'eq_fc_invoice_custom',
        'queue_job',
    ]
    
    Module = env['ir.module.module']
    
    for module_name in required_modules:
        module = Module.search([
            ('name', '=', module_name),
            ('state', '=', 'installed')
        ], limit=1)
        
        if module:
            print(f"✓ {module_name:30s} - Installed")
        else:
            print(f"✗ {module_name:30s} - NOT Installed")
    
    print()


def check_migration_config(env):
    """Check migration configurations"""
    print("\n" + "="*50)
    print("Migration Configurations")
    print("="*50)
    
    Config = env['odoo14.migration.config']
    configs = Config.search([])
    
    if not configs:
        print("⚠ No migration configurations found")
        print("  Please create a configuration in Odoo UI:")
        print("  Odoo 14 Migration → Migration Configuration")
    else:
        for config in configs:
            print(f"\nConfiguration: {config.name}")
            print(f"  URL: {config.odoo14_url}")
            print(f"  Database: {config.odoo14_database}")
            print(f"  Username: {config.odoo14_username}")
            print(f"  Active: {'Yes' if config.active else 'No'}")
    
    print()


def view_migration_status(env):
    """View vendor bill migration status"""
    print("\n" + "="*50)
    print("Vendor Bill Migration Status")
    print("="*50)
    
    MigrationLine = env['vendor.bill.migration.line']
    
    # Count by status
    statuses = [
        'pending_migration',
        'queued',
        'migrating',
        'migrated',
        'already_migrated',
        'not_found',
        'error',
    ]
    
    print("\nStatus Summary:")
    print("-" * 50)
    
    for status in statuses:
        count = MigrationLine.search_count([('status', '=', status)])
        if count > 0:
            print(f"  {status:20s}: {count:5d}")
    
    total = MigrationLine.search_count([])
    print("-" * 50)
    print(f"  {'Total':20s}: {total:5d}")
    
    # Show recent errors
    errors = MigrationLine.search([
        ('status', '=', 'error')
    ], limit=10, order='id desc')
    
    if errors:
        print("\nRecent Errors:")
        print("-" * 50)
        for error in errors:
            print(f"  {error.uploaded_bill_number:20s} - {error.error_message[:60]}")
    
    print()


def view_logs(log_file_path=None):
    """View migration logs"""
    print("\n" + "="*50)
    print("Migration Logs")
    print("="*50)
    
    if not log_file_path:
        # Try to find log file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(script_dir, 'logs', 'failed_vendor_bill_migrations.log')
    else:
        log_file = log_file_path
    
    if os.path.exists(log_file):
        print(f"\nReading log file: {log_file}\n")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                print("Last 20 entries:")
                print("-" * 50)
                for line in lines[-20:]:
                    print(f"  {line.strip()}")
            else:
                print("Log file is empty")
    else:
        print(f"⚠ Log file not found: {log_file}")
    
    print()


def upgrade_module(env, module_name='odoo14_to_19_migration'):
    """Upgrade migration module"""
    print("\n" + "="*50)
    print(f"Upgrading Module: {module_name}")
    print("="*50)
    
    Module = env['ir.module.module']
    module = Module.search([
        ('name', '=', module_name)
    ], limit=1)
    
    if not module:
        print(f"✗ Module {module_name} not found")
        return
    
    if module.state != 'installed':
        print(f"⚠ Module {module_name} is not installed")
        return
    
    try:
        module.button_immediate_upgrade()
        env.cr.commit()
        print(f"✓ Module {module_name} upgraded successfully")
    except Exception as e:
        print(f"✗ Error upgrading module: {e}")
    
    print()


def test_connection(env, config_id=None):
    """Test connection to Odoo 14"""
    print("\n" + "="*50)
    print("Testing Odoo 14 Connection")
    print("="*50)
    
    Config = env['odoo14.migration.config']
    
    if config_id:
        configs = Config.browse([config_id])
    else:
        configs = Config.search([('active', '=', True)])
    
    if not configs:
        print("⚠ No active migration configurations found")
        return
    
    for config in configs:
        print(f"\nTesting: {config.name}")
        print(f"  URL: {config.odoo14_url}")
        print(f"  Database: {config.odoo14_database}")
        
        try:
            from odoo.addons.odoo14_to_19_migration.models.odoo14_api_client import Odoo14APIClient
            
            client = Odoo14APIClient(
                url=config.odoo14_url,
                db=config.odoo14_database,
                username=config.odoo14_username,
                password=config.odoo14_password
            )
            
            if client.authenticate():
                print("  ✓ Connection successful")
                
                # Try to get version
                version = client.get_odoo_version()
                if version:
                    print(f"  ✓ Odoo version: {version}")
            else:
                print("  ✗ Authentication failed")
        except Exception as e:
            print(f"  ✗ Connection error: {e}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Vendor Bill Migration Helper Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --check                    # Check installation
  %(prog)s --status                   # View migration status
  %(prog)s --upgrade                  # Upgrade module
  %(prog)s --test-connection          # Test Odoo 14 connection
  %(prog)s --logs                     # View migration logs
        """
    )
    
    parser.add_argument(
        '-d', '--database',
        default='odoo19',
        help='Database name (default: odoo19)'
    )
    
    parser.add_argument(
        '-c', '--check',
        action='store_true',
        help='Check installation and modules'
    )
    
    parser.add_argument(
        '-s', '--status',
        action='store_true',
        help='View migration status'
    )
    
    parser.add_argument(
        '-u', '--upgrade',
        action='store_true',
        help='Upgrade migration module'
    )
    
    parser.add_argument(
        '-t', '--test-connection',
        action='store_true',
        help='Test connection to Odoo 14'
    )
    
    parser.add_argument(
        '-l', '--logs',
        action='store_true',
        help='View migration logs'
    )
    
    parser.add_argument(
        '--config-id',
        type=int,
        help='Migration configuration ID for testing connection'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all checks'
    )
    
    args = parser.parse_args()
    
    # Get environment
    env = get_env(args.database)
    
    # Run requested actions
    if args.all:
        check_modules(env)
        check_migration_config(env)
        view_migration_status(env)
        test_connection(env)
        view_logs()
    else:
        if args.check:
            check_modules(env)
            check_migration_config(env)
        
        if args.status:
            view_migration_status(env)
        
        if args.upgrade:
            upgrade_module(env)
        
        if args.test_connection:
            test_connection(env, args.config_id)
        
        if args.logs:
            view_logs()
        
        if not any([args.check, args.status, args.upgrade, args.test_connection, args.logs]):
            # Default: show status
            check_modules(env)
            view_migration_status(env)


if __name__ == '__main__':
    main()

