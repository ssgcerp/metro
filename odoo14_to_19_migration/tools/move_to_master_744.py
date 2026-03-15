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

# Accounts with remaining lines
PENDING = [
    {'id': 1814, 'name': 'VAT Input (ABU DHABI new)', 'cid': 1},
    {'id': 1803, 'name': 'VAT Input (DUBAI STORE archived)', 'cid': 7},
    {'id': 1799, 'name': 'VAT Input (BOSS FAMILY archived)', 'cid': 10},
]

def move_to_master():
    ctx = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    
    for acc in PENDING:
        src_id = acc['id']
        cid = acc['cid']
        print(f"\n--- {acc['name']} (ID {src_id}, Company {cid}) ---")
        
        line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
            [[('account_id', '=', src_id)]], {'context': ctx})
        
        print(f"  Found {len(line_ids)} lines to move.")
        
        if not line_ids:
            print("  Nothing to do.")
            continue
        
        batch_size = 100
        moved = 0
        errors = 0
        for i in range(0, len(line_ids), batch_size):
            chunk = line_ids[i:i+batch_size]
            try:
                models.execute_kw(db, uid, password, 'account.move.line', 'write',
                    [chunk, {'account_id': MASTER_ID}], {'context': ctx})
                moved += len(chunk)
                print(f"  Moved {moved}/{len(line_ids)}...", end='\r')
            except Exception as e:
                errors += 1
                print(f"\n  Error on batch {i}: {e}")
        
        print(f"\n  Done. Moved: {moved}, Errors: {errors}")
        
        remaining = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id', '=', src_id)]], {'context': ctx})
        print(f"  Remaining lines: {remaining}")

if __name__ == "__main__":
    move_to_master()
