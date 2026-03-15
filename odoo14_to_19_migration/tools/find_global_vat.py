import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def find_all_104041():
    print(f"--- Searching globally for 104041 (Iterating Companies) ---")
    
    # Get all companies
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})
    
    found_accounts = {}
    
    for c in companies:
        cid = c['id']
        cname = c['name']
        print(f"Checking context of [{cid}] {cname}...")
        
        ctx = {'allowed_company_ids': [1, cid]}
        accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', 'like', '104041')]],
            {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
            
        for a in accounts:
            if a['id'] not in found_accounts:
                found_accounts[a['id']] = a
                print(f"  FOUND: ID {a['id']} | Code: {a['code']} | Name: {a['name']} | Companies: {a['company_ids']}")

if __name__ == "__main__":
    find_all_104041()
