import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_dubai_output():
    print(f"--- Debugging Dubai (ID 3) VAT Output ---")
    
    cid = 3
    ctx = {'allowed_company_ids': [1, cid]}
    
    # Search for anything looking like VAT Output or 201017
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [['|', ('code', 'like', '201017'), ('name', 'ilike', 'VAT Output'), ('company_ids', 'in', [cid])]],
        {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
        
    print(f"Found {len(accounts)} accounts:")
    for a in accounts:
        print(f"  ID: {a['id']} | Code: {a['code']} | Name: {a['name']}")

if __name__ == "__main__":
    debug_dubai_output()
