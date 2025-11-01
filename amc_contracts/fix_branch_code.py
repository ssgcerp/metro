#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick fix script to add branch_code column to res_company table
Run this script directly or via Odoo shell
"""

import psycopg2
import sys

# Database configuration - UPDATE THESE VALUES
DB_NAME = "metro1"  # Change to your database name
DB_USER = "odoo"    # Change to your database user
DB_PASSWORD = "odoo"  # Change to your database password
DB_HOST = "localhost"
DB_PORT = "5432"

def add_branch_code_column():
    """Add branch_code column to res_company table"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        # Check if column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='res_company' AND column_name='branch_code'
        """)
        
        if cur.fetchone():
            print("✓ Column 'branch_code' already exists in res_company table")
        else:
            # Add the column
            cur.execute("""
                ALTER TABLE res_company 
                ADD COLUMN branch_code VARCHAR(10)
            """)
            conn.commit()
            print("✓ Successfully added 'branch_code' column to res_company table")
        
        cur.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"✗ Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Adding branch_code column to res_company table...")
    print(f"Database: {DB_NAME}")
    print("-" * 50)
    
    # Get database credentials from command line if provided
    if len(sys.argv) >= 4:
        DB_NAME = sys.argv[1]
        DB_USER = sys.argv[2]
        DB_PASSWORD = sys.argv[3]
        if len(sys.argv) >= 5:
            DB_HOST = sys.argv[4]
        if len(sys.argv) >= 6:
            DB_PORT = sys.argv[5]
    
    success = add_branch_code_column()
    
    if success:
        print("-" * 50)
        print("✓ Done! Please restart Odoo server or refresh your browser.")
    else:
        print("-" * 50)
        print("✗ Failed! Please check your database credentials and try again.")
        print("\nUsage:")
        print("  python fix_branch_code.py [dbname] [user] [password] [host] [port]")
        print("\nExample:")
        print("  python fix_branch_code.py metro1 odoo odoo localhost 5432")






