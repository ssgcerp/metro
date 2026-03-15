import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def inspect_specifics():
    print(f"--- Inspecting Specific Accounts ---")
    
    # Check ID 1802 explicitly (Dubai Master)
    ctx = {'allowed_company_ids': [1, 3]}
    acc1802 = models.execute_kw(db, uid, password, 'account.account', 'read', [[1802], ['id', 'name', 'code', 'company_ids', 'active']], {'context': ctx})
    print(f"ID 1802: {acc1802}")
    
    # Check if any account has code 201017C3TMP in ANY company
    print("Searching for 201017C3TMP in ALL companies...")
    companies = models.execute_kw(db, uid, password, 'res.company', 'search', [[]])
    ctx_all = {'allowed_company_ids': companies, 'active_test': False}
    
    bad_accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'ilike', '201017C3TMP')]],
        {'fields': ['id', 'name', 'code', 'company_ids', 'active'], 'context': ctx_all})
        
    print(f"Bad Accounts Found: {len(bad_accs)}")
    for a in bad_accs:
        print(f"  BAD: {a}")

if __name__ == "__main__":
    inspect_specifics()
