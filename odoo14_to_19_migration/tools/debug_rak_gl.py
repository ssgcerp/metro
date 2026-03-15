import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_rak_gl():
    RAK_ID = 2
    
    print("--- 1. Check Account status for RAK ---")
    try:
        # Context to allow seeing RAK data
        ctx = {'allowed_company_ids': [1, RAK_ID]}
        
        # Search for 104041 accessible to RAK
        # Use company_ids in domain
        domain = ['&', ('code', '=', '104041'), '|', ('company_ids', 'in', [RAK_ID]), ('company_ids', '=', False)]
        accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [domain],
            {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
            
        print(f"Found {len(accounts)} accounts for code 104041 available to RAK:")
        for acc in accounts:
            print(f" - ID: {acc['id']} | Name: {acc['name']} | Companies: {acc['company_ids']}")
            
            # Check entries count
            count = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
                [[('account_id', '=', acc['id']), ('company_id', '=', RAK_ID)]],
                {'context': ctx})
            print(f"   -> Entry Count for RAK: {count}")

        print("\n--- 2. Search for 'Lost' VAT entries in RAK ---")
        
        # Get IDs of known VAT accounts to exclude (if any)
        known_vat_ids = [a['id'] for a in accounts]
        
        print(f"Excluding known VAT IDs: {known_vat_ids}")
        
        # Search for move lines in RAK that have 'VAT' in name but are NOT on the known accounts
        lost_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
            [[('company_id', '=', RAK_ID), ('name', 'ilike', 'VAT'), ('account_id', 'not in', known_vat_ids)]],
            {'fields': ['id', 'name', 'account_id', 'date', 'move_id'], 'limit': 20, 'context': ctx})
            
        if lost_lines:
            print(f"Found {len(lost_lines)} suspicious 'VAT' lines on OTHER accounts:")
            for l in lost_lines:
                # Read account name carefully
                acc_info = models.execute_kw(db, uid, password, 'account.account', 'read', 
                    [[l['account_id'][0]], ['name', 'code']], {'context': ctx})
                acc_name = acc_info[0] if acc_info else {'name': 'Unknown', 'code': '?'}
                print(f" - Date: {l['date']} | Desc: {l['name']} | On Account: [{acc_name['code']}] {acc_name['name']}")
        else:
            print("No suspicious 'VAT' lines found on other accounts.")
            
    except Exception as e:
        print(f"Error during debug: {e}")
        
    print("\n--- 3. Check for Suspense/Off-Balance VAT ---")
    # Sometimes taxes go to a generic account if configuration is wrong.

if __name__ == "__main__":
    debug_rak_gl()
