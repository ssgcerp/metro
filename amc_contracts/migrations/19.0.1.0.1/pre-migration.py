# -*- coding: utf-8 -*-

def migrate(cr, version):
    """Add branch_code column to res_company table if it doesn't exist"""
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='res_company' AND column_name='branch_code'
    """)
    
    if not cr.fetchone():
        cr.execute("""
            ALTER TABLE res_company 
            ADD COLUMN branch_code VARCHAR(10)
        """)
