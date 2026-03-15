import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def verify_counts():
    companies = [2, 3, 5, 8] # RAK, Dubai, Ajman, Mysore
    
    print("--- Verifying Final VAT Input (104041) Status ---")
    
    for cid in companies:
        ctx = {'allowed_company_ids': [1, cid]}
        # Search ACTIVE only
        accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', 'like', '104041'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
            
        print(f"Company {cid}: Found {len(accounts)} accounts.")
        for a in accounts:
            print(f"  ID: {a['id']} | Code: {a['code']} | Name: {a['name']}")

if __name__ == "__main__":
    verify_counts()
