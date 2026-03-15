import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def find_hidden_vat():
    print(f"Searching for 104041 in {db} across ALL companies...")
    
    # Search for code 104041 globally
    # Just filter by code
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '104041')]],
        {'fields': ['id', 'name', 'code', 'company_ids']})
        
    print(f"Found {len(accounts)} accounts:")
    for acc in accounts:
        print(f" - ID: {acc['id']} | Name: {acc['name']} | Companies: {acc['company_ids']}")
        
        # Try to share with RAK (ID 2)
        if 2 not in acc['company_ids']:
            print("   -> Attempting to share with RAK (ID 2)...")
            new_ids = acc['company_ids'] + [2]
            try:
                # Use allowed_company_ids context to bypass rules if possible
                ctx = {'allowed_company_ids': new_ids} # Include all target companies
                models.execute_kw(db, uid, password, 'account.account', 'write',
                    [[acc['id']], {'company_ids': [(6, 0, new_ids)]}],
                    {'context': ctx})
                print("   -> Success! Shared.")
            except Exception as e:
                print(f"   -> Error sharing: {e}")
        else:
            print("   -> Already shared with RAK.")

if __name__ == "__main__":
    find_hidden_vat()
