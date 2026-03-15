"""
Script to merge ALL 104041 VAT Input accounts into Master ID 744
and add all companies to it via direct DB manipulation.

Run this via: python merge_all_to_744.py
"""
import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

ALL_COMPANIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
MASTER_ID = 744

def merge_all():
    ctx = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    
    print("=== Step 1: Find all 104041 accounts (active + archived) ===")
    accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'like', '104041')]],
        {'fields': ['id', 'name', 'code', 'active', 'company_ids'], 'context': ctx})
    
    # Separate master from others
    others = [a for a in accs if a['id'] != MASTER_ID]
    master = next((a for a in accs if a['id'] == MASTER_ID), None)
    
    print(f"Master (ID {MASTER_ID}): {master}")
    print(f"Others to merge: {len(others)}")
    for a in others:
        print(f"  ID {a['id']} | Code: {a['code']} | Active: {a['active']} | Companies: {a['company_ids']}")
    
    print("\n=== Step 2: Move all lines from other accounts to Master 744 ===")
    for acc in others:
        src_id = acc['id']
        line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
            [[('account_id', '=', src_id)]], {'context': ctx})
        
        if not line_ids:
            print(f"  ID {src_id}: No lines. Skipping.")
            continue
        
        print(f"  ID {src_id} ({acc['name']}): Moving {len(line_ids)} lines...")
        
        # Try moving with all companies in context
        batch_size = 100
        moved = 0
        errors = 0
        for i in range(0, len(line_ids), batch_size):
            chunk = line_ids[i:i+batch_size]
            try:
                models.execute_kw(db, uid, password, 'account.move.line', 'write',
                    [chunk, {'account_id': MASTER_ID}], {'context': ctx})
                moved += len(chunk)
            except Exception as e:
                errors += 1
                print(f"    Error on batch {i}: {e}")
        
        print(f"  Done. Moved: {moved}, Errors: {errors}")
    
    print("\n=== Step 3: Add all companies to Master 744 ===")
    # Get current companies on master
    master_now = models.execute_kw(db, uid, password, 'account.account', 'read',
        [[MASTER_ID]], {'fields': ['company_ids'], 'context': ctx})
    current = set(master_now[0]['company_ids'])
    missing = [c for c in ALL_COMPANIES if c not in current]
    print(f"Current companies on 744: {list(current)}")
    print(f"Missing companies: {missing}")
    
    if missing:
        try:
            add_cmds = [(4, c) for c in missing]
            models.execute_kw(db, uid, password, 'account.account', 'write',
                [[MASTER_ID], {'company_ids': add_cmds}], {'context': ctx})
            print("  Added missing companies.")
        except Exception as e:
            print(f"  Error adding companies: {e}")
            print("  NOTE: This may require direct DB access. See instructions below.")
    
    print("\n=== Step 4: Verify ===")
    master_final = models.execute_kw(db, uid, password, 'account.account', 'read',
        [[MASTER_ID]], {'fields': ['name', 'code', 'company_ids'], 'context': ctx})
    print(f"Master 744 final state: {master_final[0]}")
    
    # Count remaining lines on other accounts
    total_remaining = 0
    for acc in others:
        remaining = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id', '=', acc['id'])]], {'context': ctx})
        if remaining > 0:
            print(f"  WARNING: ID {acc['id']} still has {remaining} lines!")
            total_remaining += remaining
    
    if total_remaining == 0:
        print("\n✓ All lines successfully moved to Master 744!")
    else:
        print(f"\n✗ {total_remaining} lines still on other accounts. Manual intervention needed.")

if __name__ == "__main__":
    merge_all()
