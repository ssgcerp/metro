#!/usr/bin/env python3
"""
Real-time Migration Monitor and Trigger
Usage:
    python migration_monitor.py --trigger --quotation-numbers S00031,S00032,S00033
    python migration_monitor.py --monitor
    python migration_monitor.py --trigger-all-pending
"""

import argparse
import sys
import time
from datetime import datetime
from xmlrpc import client as xmlrpc_client

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_status(message, color=Colors.WHITE):
    """Print colored status message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}]{Colors.RESET} {message}")

def connect_odoo(url, db, username, password):
    """Connect to Odoo via XML-RPC"""
    try:
        common = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        if not uid:
            print_status("❌ Authentication failed", Colors.RED)
            sys.exit(1)
        
        models = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/object')
        print_status(f"✅ Connected to Odoo: {url}", Colors.GREEN)
        return models, uid, db
    except Exception as e:
        print_status(f"❌ Connection error: {str(e)}", Colors.RED)
        sys.exit(1)

def trigger_bulk_migration(models, uid, db, password, quotation_numbers):
    """Trigger bulk migration for specific quotation numbers"""
    print_status(f"🚀 Triggering migration for {len(quotation_numbers)} quotations...", Colors.CYAN)
    
    # First, upload the quotations
    quotation_ids = []
    for qty_num in quotation_numbers:
        # Search for existing record
        existing = models.execute_kw(
            db, uid, password,
            'eq.migration.quotation', 'search',
            [[('uploaded_quotation_number', '=', qty_num)]],
            {'limit': 1}
        )
        
        if existing:
            quotation_ids.append(existing[0])
        else:
            # Create new record
            record_id = models.execute_kw(
                db, uid, password,
                'eq.migration.quotation', 'create',
                [{'uploaded_quotation_number': qty_num}]
            )
            quotation_ids.append(record_id)
    
    # Trigger bulk migration
    try:
        result = models.execute_kw(
            db, uid, password,
            'eq.migration.quotation', 'action_bulk_migrate',
            [quotation_ids]
        )
        print_status(f"✅ Migration triggered for {len(quotation_ids)} quotations", Colors.GREEN)
        return quotation_ids
    except Exception as e:
        print_status(f"❌ Error triggering migration: {str(e)}", Colors.RED)
        return []

def trigger_all_pending(models, uid, db, password):
    """Trigger migration for all pending quotations"""
    print_status("🔍 Finding all pending quotations...", Colors.CYAN)
    
    pending_ids = models.execute_kw(
        db, uid, password,
        'eq.migration.quotation', 'search',
        [[('status', 'in', ['pending_migration', 'queued'])]]
    )
    
    if not pending_ids:
        print_status("ℹ️  No pending quotations found", Colors.YELLOW)
        return []
    
    print_status(f"📋 Found {len(pending_ids)} pending quotations", Colors.CYAN)
    
    # Trigger bulk migration
    try:
        result = models.execute_kw(
            db, uid, password,
            'eq.migration.quotation', 'action_bulk_migrate',
            [pending_ids]
        )
        print_status(f"✅ Migration triggered for {len(pending_ids)} quotations", Colors.GREEN)
        return pending_ids
    except Exception as e:
        print_status(f"❌ Error triggering migration: {str(e)}", Colors.RED)
        return []

def get_status(models, uid, db, password, record_ids=None):
    """Get current status of migration records"""
    if record_ids:
        domain = [('id', 'in', record_ids)]
    else:
        domain = []
    
    records = models.execute_kw(
        db, uid, password,
        'eq.migration.quotation', 'search_read',
        [domain],
        {
            'fields': ['id', 'uploaded_quotation_number', 'in_system_quotation_number', 
                      'status', 'status_message', 'migration_date', 'error_message'],
            'order': 'id desc'
        }
    )
    
    return records

def print_status_table(records):
    """Print status in a formatted table"""
    if not records:
        return
    
    # Count by status
    status_count = {}
    for rec in records:
        status = rec.get('status', 'unknown')
        status_count[status] = status_count.get(status, 0) + 1
    
    # Print summary
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}Migration Status Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
    
    status_colors = {
        'migrated': Colors.GREEN,
        'migrating': Colors.CYAN,
        'queued': Colors.YELLOW,
        'pending_migration': Colors.YELLOW,
        'error': Colors.RED,
        'not_found': Colors.RED,
        'already_migrated': Colors.BLUE,
    }
    
    for status, count in sorted(status_count.items()):
        color = status_colors.get(status, Colors.WHITE)
        status_display = status.replace('_', ' ').title()
        print(f"  {color}{status_display:20s}{Colors.RESET}: {count:3d}")
    
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")
    
    # Print detailed table
    print(f"{Colors.BOLD}{'Quotation':<15} {'Status':<20} {'Message':<30} {'Date':<20}{Colors.RESET}")
    print(f"{'-'*85}")
    
    for rec in records[:20]:  # Show first 20
        qty_num = rec.get('uploaded_quotation_number', 'N/A')
        status = rec.get('status', 'unknown')
        message = rec.get('status_message', '') or rec.get('error_message', '') or ''
        migration_date = rec.get('migration_date', '')
        
        if len(message) > 28:
            message = message[:25] + '...'
        
        color = status_colors.get(status, Colors.WHITE)
        status_display = status.replace('_', ' ').title()
        
        print(f"{qty_num:<15} {color}{status_display:<20}{Colors.RESET} {message:<30} {migration_date[:19] if migration_date else '':<20}")
    
    if len(records) > 20:
        print(f"\n... and {len(records) - 20} more records")

def monitor_status(models, uid, db, password, record_ids=None, interval=2):
    """Monitor migration status in real-time"""
    print_status("👀 Starting real-time monitoring...", Colors.CYAN)
    print_status("Press Ctrl+C to stop\n", Colors.YELLOW)
    
    previous_status = {}
    
    try:
        while True:
            records = get_status(models, uid, db, password, record_ids)
            
            # Check for status changes
            current_status = {rec['id']: rec.get('status') for rec in records}
            
            # Detect changes
            for rec in records:
                rec_id = rec['id']
                old_status = previous_status.get(rec_id)
                new_status = rec.get('status')
                
                if old_status and old_status != new_status:
                    qty_num = rec.get('uploaded_quotation_number', 'N/A')
                    print_status(
                        f"🔄 {qty_num}: {old_status} → {new_status}",
                        Colors.CYAN
                    )
            
            previous_status = current_status
            
            # Clear screen and print status
            print("\033[2J\033[H")  # Clear screen
            print_status_table(records)
            
            # Check if all are done
            all_done = all(
                rec.get('status') in ('migrated', 'error', 'not_found', 'already_migrated')
                for rec in records
            )
            
            if all_done and records:
                print_status("✅ All migrations completed!", Colors.GREEN)
                break
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print_status("\n⏹️  Monitoring stopped by user", Colors.YELLOW)
        # Show final status
        records = get_status(models, uid, db, password, record_ids)
        print_status_table(records)

def main():
    parser = argparse.ArgumentParser(
        description='Odoo 14 to 19 Migration Monitor and Trigger',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor all migrations in real-time
  python migration_monitor.py --monitor

  # Trigger migration for specific quotations
  python migration_monitor.py --trigger --quotation-numbers S00031,S00032,S00033

  # Trigger all pending migrations
  python migration_monitor.py --trigger-all-pending

  # Monitor specific quotations
  python migration_monitor.py --monitor --quotation-numbers S00031,S00032
        """
    )
    
    parser.add_argument('--url', default='http://localhost:8079',
                       help='Odoo URL (default: http://localhost:8079)')
    parser.add_argument('--db', default='metrodb',
                       help='Database name (default: metrodb)')
    parser.add_argument('--username', default='admin',
                       help='Username (default: admin)')
    parser.add_argument('--password', required=True,
                       help='Password (required)')
    parser.add_argument('--trigger', action='store_true',
                       help='Trigger migration for specified quotations')
    parser.add_argument('--trigger-all-pending', action='store_true',
                       help='Trigger migration for all pending quotations')
    parser.add_argument('--monitor', action='store_true',
                       help='Monitor migration status in real-time')
    parser.add_argument('--quotation-numbers', type=str,
                       help='Comma-separated list of quotation numbers (e.g., S00031,S00032)')
    parser.add_argument('--interval', type=int, default=2,
                       help='Monitoring refresh interval in seconds (default: 2)')
    
    args = parser.parse_args()
    
    # Connect to Odoo
    models, uid, db = connect_odoo(args.url, args.db, args.username, args.password)
    
    record_ids = None
    
    # Trigger migrations if requested
    if args.trigger:
        if not args.quotation_numbers:
            print_status("❌ --quotation-numbers is required with --trigger", Colors.RED)
            sys.exit(1)
        
        quotation_numbers = [q.strip() for q in args.quotation_numbers.split(',')]
        record_ids = trigger_bulk_migration(models, uid, db, args.password, quotation_numbers)
        
        if not record_ids:
            sys.exit(1)
    
    elif args.trigger_all_pending:
        record_ids = trigger_all_pending(models, uid, db, args.password)
        
        if not record_ids:
            sys.exit(0)
    
    # Monitor if requested
    if args.monitor:
        # If quotation numbers specified, get their IDs
        if args.quotation_numbers:
            quotation_numbers = [q.strip() for q in args.quotation_numbers.split(',')]
            record_ids = models.execute_kw(
                db, uid, args.password,
                'eq.migration.quotation', 'search',
                [[('uploaded_quotation_number', 'in', quotation_numbers)]]
            )
        
        monitor_status(models, uid, db, args.password, record_ids, args.interval)
    
    elif not args.trigger and not args.trigger_all_pending:
        # Just show current status
        records = get_status(models, uid, db, args.password, record_ids)
        print_status_table(records)

if __name__ == '__main__':
    main()
