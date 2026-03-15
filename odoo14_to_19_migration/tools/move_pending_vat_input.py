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
PENDING = [
    {'id': 40,   'name': 'VAT Input (ABU DHABI)',   'lines': 3662},
    {'id': 1799, 'name': 'VAT Input (BOSS FAMILY)',  'lines': 5},
    {'id': 1811, 'name': 'VAT Input (SHARJAH)',      'lines': 881},
    {'id': 1807, 'name': 'VAT Input (FUJAIRAH)',     'lines': 1239},
    {'id': 1803, 'name': 'VAT Input (DUBAI STORE)',  'lines': 291},
]

def move_lines():
    ctx = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    
    for acc in PENDING:
        acc_id = acc['id']
        print(f"\n--- Processing {acc['name']} (ID {acc_id}) ---")
        
        # Get all line IDs
        line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
            [[('account_id', '=', acc_id)]], {'context': ctx})
        
        print(f"  Found {len(line_ids)} lines to move.")
        
        if not line_ids:
            print("  Nothing to do.")
            continue
        
        # Move in batches of 100
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
        
        # Verify
        remaining = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id', '=', acc_id)]], {'context': ctx})
        print(f"  Remaining lines on account: {remaining}")

if __name__ == "__main__":
    move_lines()
