"""
Direct PostgreSQL approach to:
1. Add all companies to account.account ID 744
2. Move all lines from other 104041 accounts to 744

Uses psycopg2 to connect directly to the database.
"""
import psycopg2

# DB connection
conn = psycopg2.connect(
    host="metro.equdaierp.com",
    port=5432,
    dbname="metrodb",
    user="odoo",
    password="Amaze@321"
)
conn.autocommit = False
cur = conn.cursor()

MASTER_ID = 744

try:
    print("=== Step 1: Check current companies on Master 744 ===")
    cur.execute("""
        SELECT res_company_id FROM account_account_res_company_rel 
        WHERE account_account_id = %s ORDER BY res_company_id
    """, [MASTER_ID])
    current = [r[0] for r in cur.fetchall()]
    print(f"Current companies: {current}")
    
    print("\n=== Step 2: Add ALL companies to Master 744 ===")
    cur.execute("""
        INSERT INTO account_account_res_company_rel (account_account_id, res_company_id)
        SELECT %s, id FROM res_company
        WHERE id NOT IN (
            SELECT res_company_id FROM account_account_res_company_rel 
            WHERE account_account_id = %s
        )
    """, [MASTER_ID, MASTER_ID])
    print(f"  Inserted {cur.rowcount} new company relations.")
    
    print("\n=== Step 3: Find all other 104041 accounts ===")
    cur.execute("""
        SELECT id, name, code, active FROM account_account 
        WHERE code LIKE '104041%' AND id != %s
        ORDER BY id
    """, [MASTER_ID])
    others = cur.fetchall()
    print(f"Found {len(others)} other accounts:")
    for o in others:
        cur.execute("SELECT COUNT(*) FROM account_move_line WHERE account_id = %s", [o[0]])
        cnt = cur.fetchone()[0]
        print(f"  ID {o[0]} | {o[1]} | Code: {o[2]} | Active: {o[3]} | Lines: {cnt}")
    
    print("\n=== Step 4: Move all lines to Master 744 ===")
    for acc in others:
        src_id = acc[0]
        cur.execute("SELECT COUNT(*) FROM account_move_line WHERE account_id = %s", [src_id])
        count = cur.fetchone()[0]
        
        if count == 0:
            print(f"  ID {src_id}: No lines.")
            continue
        
        print(f"  ID {src_id} ({acc[1]}): Moving {count} lines...")
        cur.execute("UPDATE account_move_line SET account_id = %s WHERE account_id = %s", [MASTER_ID, src_id])
        print(f"  Moved {cur.rowcount} lines.")
    
    print("\n=== Step 5: Commit ===")
    conn.commit()
    print("Committed!")
    
    print("\n=== Step 6: Final Verification ===")
    cur.execute("""
        SELECT aa.id, aa.name, aa.code, aa.active,
               array_agg(rel.res_company_id ORDER BY rel.res_company_id) as companies,
               (SELECT COUNT(*) FROM account_move_line WHERE account_id = aa.id) as lines
        FROM account_account aa
        LEFT JOIN account_account_res_company_rel rel ON rel.account_account_id = aa.id
        WHERE aa.code LIKE '104041%'
        GROUP BY aa.id, aa.name, aa.code, aa.active
        ORDER BY aa.id
    """)
    rows = cur.fetchall()
    print(f"{'ID':<8} {'Code':<15} {'Active':<8} {'Lines':<8} {'Companies'}")
    print("-" * 80)
    for r in rows:
        print(f"{r[0]:<8} {r[2]:<15} {str(r[3]):<8} {r[5]:<8} {r[4]}")

except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
    raise
finally:
    cur.close()
    conn.close()
