import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def dump_and_check():
    print(f"--- Listing All Companies ---")
    comps = models.execute_kw(db, uid, password, 'res.company', 'search_read', [], {'fields': ['id', 'name']})
    for c in comps:
        print(f"  ID: {c['id']} | Name: {c['name']}")
        
    print(f"\n--- Dumping Accounts for Dubai (ID 3) and RAK (ID 2) ---")
    # We use a broad context
    ctx = {'allowed_company_ids': [1, 2, 3, 5, 8], 'active_test': False}
    
    # Fetch ALL accounts for these companies
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('company_ids', 'in', [2, 3])]],
        {'fields': ['id', 'name', 'code', 'company_ids', 'active'], 'context': ctx})
        
    print(f"Total Accounts Found: {len(accounts)}")
    for a in accounts:
        # manual filter for 2010 or Output to keep output manageable, but loose enough
        if '201017' in str(a['code']) or 'VAT' in a['name'] or 'TMP' in str(a['code']) or 'Output' in a['name']:
            print(f"  ACC: {a}")

if __name__ == "__main__":
    dump_and_check()
