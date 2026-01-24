# -*- coding: utf-8 -*-
"""Pre-migration script to remove migration_cron model table"""

def migrate(cr, version):
    """Drop odoo14_migration_cron table if it exists"""
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'odoo14_migration_cron'
        );
    """)
    table_exists = cr.fetchone()[0]
    
    if table_exists:
        # Drop the table
        cr.execute("DROP TABLE IF EXISTS odoo14_migration_cron CASCADE;")
        # Also drop any related sequences
        cr.execute("DROP SEQUENCE IF EXISTS odoo14_migration_cron_id_seq CASCADE;")
        cr.commit()
        print("Dropped odoo14_migration_cron table and related objects")
