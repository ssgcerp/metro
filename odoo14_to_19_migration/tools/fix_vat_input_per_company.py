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

# Accounts with remaining lines to move
# Key: company_id -> source account id
PENDING = {
    1:  {'src_id': 40,   'name': 'VAT Input (ABU DHABI)',   'lines': 3662},
    10: {'src_id': 1799, 'name': 'VAT Input (BOSS FAMILY)',  'lines': 5},
    4:  {'src_id': 1811, 'name': 'VAT Input (SHARJAH)',      'lines': 881},
    6:  {'src_id': 1807, 'name': 'VAT Input (FUJAIRAH)',     'lines': 1239},
    7:  {'src_id': 1803, 'name': 'VAT Input (DUBAI STORE)',  'lines': 291},
}

def fix_per_company():
    """
    For each company with pending lines, find or create a proper 104041 account
    for that company, then move lines from the archived duplicate to it.
    """
    ctx = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    
    for cid, info in PENDING.items():
        src_id = info['src_id']
        print(f"\n--- Company {cid} | Source Account {src_id} ({info['name']}) ---")
        
        # 1. Find existing active 104041 for this company (not the archived one)
        existing = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', '=', '104041'), ('company_ids', 'in', [cid]), ('active', '=', True)]],
            {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
        
        if existing:
            target_id = existing[0]['id']
            print(f"  Found existing active account: ID {target_id} | {existing[0]['name']}")
        else:
            # 2. Create a new account for this company
            print(f"  No active 104041 found for company {cid}. Creating...")
            # Get company name
            comp = models.execute_kw(db, uid, password, 'res.company', 'read', [[cid]], {'fields': ['name']})
            comp_name = comp[0]['name'] if comp else f'Company {cid}'
            
            # Get account type from master
            master = models.execute_kw(db, uid, password, 'account.account', 'read', 
                [[MASTER_ID]], {'fields': ['account_type', 'reconcile', 'currency_id'], 'context': ctx})
            
            new_vals = {
                'name': f'VAT Input',
                'code': '104041',
                'account_type': master[0]['account_type'],
                'company_ids': [(4, cid)],
            }
            try:
                target_id = models.execute_kw(db, uid, password, 'account.account', 'create', 
                    [new_vals], {'context': {'allowed_company_ids': [cid]}})
                print(f"  Created new account ID {target_id}")
            except Exception as e:
                print(f"  Error creating account: {e}")
                continue
        
        # 3. Move lines from src_id to target_id
        line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
            [[('account_id', '=', src_id)]], {'context': ctx})
        
        print(f"  Moving {len(line_ids)} lines from {src_id} -> {target_id}...")
        
        batch_size = 100
        moved = 0
        errors = 0
        for i in range(0, len(line_ids), batch_size):
            chunk = line_ids[i:i+batch_size]
            try:
                models.execute_kw(db, uid, password, 'account.move.line', 'write',
                    [chunk, {'account_id': target_id}], {'context': ctx})
                moved += len(chunk)
                print(f"  Moved {moved}/{len(line_ids)}...", end='\r')
            except Exception as e:
                errors += 1
                print(f"\n  Error on batch {i}: {e}")
        
        print(f"\n  Done. Moved: {moved}, Errors: {errors}")
        
        # 4. Verify
        remaining = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id', '=', src_id)]], {'context': ctx})
        print(f"  Remaining lines on source: {remaining}")

if __name__ == "__main__":
    fix_per_company()
