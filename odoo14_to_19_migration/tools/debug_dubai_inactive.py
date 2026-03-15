import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_dubai_inactive():
    print(f"--- Debugging Dubai (ID 3) Inactive/All VAT Output ---")
    
    cid = 3
    ctx = {'allowed_company_ids': [1, cid], 'active_test': False} # Search all including inactive
    
    # Search for anything looking like VAT Output or 201017 or TMP
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [['|', '|', ('code', 'like', '201017'), ('name', 'ilike', 'VAT Output'), ('code', 'like', 'TMP'), ('company_ids', 'in', [cid])]],
        {'fields': ['id', 'name', 'code', 'company_ids', 'active'], 'context': ctx})
        
    print(f"Found {len(accounts)} accounts (Active & Inactive):")
    for a in accounts:
        print(f"  ID: {a['id']} | Code: {a['code']} | Name: {a['name']} | Active: {a['active']}")

if __name__ == "__main__":
    debug_dubai_inactive()
