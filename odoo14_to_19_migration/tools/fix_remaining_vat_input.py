import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

ALL_COMPANIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# BOSS FAMILY = company 10, src = 1799 (5 lines)
# DUBAI STORE = company 7, src = 1803 (291 lines)
REMAINING = [
    {'cid': 10, 'src_id': 1799, 'name': 'BOSS FAMILY'},
    {'cid': 7,  'src_id': 1803, 'name': 'DUBAI STORE'},
]

def fix_remaining():
    ctx_all = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    
    # Get account type from master
    master = models.execute_kw(db, uid, password, 'account.account', 'read', 
        [[744]], {'fields': ['account_type'], 'context': ctx_all})
    acc_type = master[0]['account_type']
    
    for item in REMAINING:
        cid = item['cid']
        src_id = item['src_id']
        print(f"\n--- {item['name']} (Company {cid}) ---")
        
        # Create with single-company context to avoid multi-company constraint
        ctx_single = {'allowed_company_ids': [cid]}
        print(f"  Creating new 104041 for company {cid} (single-company context)...")
        try:
            target_id = models.execute_kw(db, uid, password, 'account.account', 'create', 
                [{'name': 'VAT Input', 'code': '104041', 'account_type': acc_type}],
                {'context': ctx_single})
            print(f"  Created ID {target_id}")
        except Exception as e:
            print(f"  Error creating: {e}")
            continue
        
        # Move lines
        line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
            [[('account_id', '=', src_id)]], {'context': ctx_all})
        
        print(f"  Moving {len(line_ids)} lines from {src_id} -> {target_id}...")
        
        batch_size = 100
        moved = 0
        errors = 0
        for i in range(0, len(line_ids), batch_size):
            chunk = line_ids[i:i+batch_size]
            try:
                models.execute_kw(db, uid, password, 'account.move.line', 'write',
                    [chunk, {'account_id': target_id}], {'context': ctx_all})
                moved += len(chunk)
            except Exception as e:
                errors += 1
                print(f"\n  Error on batch {i}: {e}")
        
        print(f"  Done. Moved: {moved}, Errors: {errors}")
        
        remaining = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id', '=', src_id)]], {'context': ctx_all})
        print(f"  Remaining lines on source: {remaining}")

if __name__ == "__main__":
    fix_remaining()
