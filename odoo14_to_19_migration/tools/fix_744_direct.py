"""
Direct DB approach to:
1. Add all companies to account.account ID 744 via SQL
2. Move all lines from other 104041 accounts to 744

Run via Odoo shell: odoo shell -d metrodb --no-http
Then: exec(open('fix_744_direct.py').read())
"""

# This script is meant to be run inside Odoo shell
# Usage: odoo shell -d metrodb --no-http < fix_744_direct.py

MASTER_ID = 744
ALL_COMPANY_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Step 1: Add all companies to Master 744 via direct SQL
print("=== Adding all companies to Master 744 ===")
env.cr.execute("""
    INSERT INTO account_account_res_company_rel (account_account_id, res_company_id)
    SELECT %s, id FROM res_company
    WHERE id NOT IN (
        SELECT res_company_id FROM account_account_res_company_rel 
        WHERE account_account_id = %s
    )
""", [MASTER_ID, MASTER_ID])
print(f"  Inserted {env.cr.rowcount} company relations.")

# Step 2: Find all other 104041 accounts
env.cr.execute("""
    SELECT id, name, code, active FROM account_account 
    WHERE code LIKE '104041%' AND id != %s
""", [MASTER_ID])
others = env.cr.fetchall()
print(f"\n=== Found {len(others)} other 104041 accounts ===")
for o in others:
    print(f"  ID {o[0]} | {o[1]} | Code: {o[2]} | Active: {o[3]}")

# Step 3: Move all lines to Master 744
print("\n=== Moving lines to Master 744 ===")
for acc in others:
    src_id = acc[0]
    env.cr.execute("""
        SELECT COUNT(*) FROM account_move_line WHERE account_id = %s
    """, [src_id])
    count = env.cr.fetchone()[0]
    
    if count == 0:
        print(f"  ID {src_id}: No lines.")
        continue
    
    print(f"  ID {src_id} ({acc[1]}): Moving {count} lines...")
    env.cr.execute("""
        UPDATE account_move_line SET account_id = %s WHERE account_id = %s
    """, [MASTER_ID, src_id])
    print(f"  Moved {env.cr.rowcount} lines.")

# Step 4: Commit
env.cr.commit()
print("\n=== Committed! ===")

# Step 5: Verify
env.cr.execute("""
    SELECT aa.id, aa.name, aa.code, aa.active,
           array_agg(rel.res_company_id) as companies,
           (SELECT COUNT(*) FROM account_move_line WHERE account_id = aa.id) as lines
    FROM account_account aa
    LEFT JOIN account_account_res_company_rel rel ON rel.account_account_id = aa.id
    WHERE aa.code LIKE '104041%'
    GROUP BY aa.id, aa.name, aa.code, aa.active
    ORDER BY aa.id
""")
rows = env.cr.fetchall()
print("\n=== Final State ===")
for r in rows:
    print(f"  ID {r[0]} | {r[1]} | Code: {r[2]} | Active: {r[3]} | Companies: {r[4]} | Lines: {r[5]}")
