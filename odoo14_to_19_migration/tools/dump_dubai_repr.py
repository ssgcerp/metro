import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def dump_repr():
    print(f"--- Dumping Dubai (ID 3) Accounts with REPR ---")
    
    ctx = {'allowed_company_ids': [1, 3], 'active_test': False} # Include archived
    
    # Get ALL accounts for Dubai
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('company_ids', 'in', [3])]],
        {'fields': ['id', 'name', 'code', 'display_name'], 'context': ctx})
        
    print(f"Total Accounts: {len(accounts)}")
    
    match_count = 0
    for a in accounts:
        # Check if code starts with 20
        if str(a['code']).startswith('20') or 'TMP' in str(a['code']) or 'VAT' in a['name']:
             print(f"ID: {a['id']}")
             print(f"  Code: {repr(a['code'])}")
             print(f"  Name: {repr(a['name'])}")
             print(f"  Display: {repr(a['display_name'])}")
             match_count += 1
             
    print(f"Printed {match_count} potentials.")

if __name__ == "__main__":
    dump_repr()
