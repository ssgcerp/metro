# -*- coding: utf-8 -*-

from . import models

def post_init_hook(env):
    """Create branch_code column after module installation/upgrade"""
    cr = env.cr
    try:
        cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='res_company' AND column_name='branch_code'
        """)
        
        if not cr.fetchone():
            cr.execute("""
                ALTER TABLE res_company 
                ADD COLUMN IF NOT EXISTS branch_code VARCHAR(10)
            """)
            cr.commit()
            print("✓ Added branch_code column to res_company table")
    except Exception as e:
        cr.rollback()
        print(f"⚠ Warning: Could not add branch_code column: {e}")
        print("Please run the SQL manually: ALTER TABLE res_company ADD COLUMN branch_code VARCHAR(10);")

def uninstall_hook(env):
    """Optional: Remove branch_code column on module uninstall"""
    cr = env.cr
    # Uncomment if you want to remove the column on uninstall
    # cr.execute("""
    #     ALTER TABLE res_company 
    #     DROP COLUMN IF EXISTS branch_code
    # """)
    pass
