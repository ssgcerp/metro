import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_dubai_tmp():
    print(f"--- Searching Dubai (ID 3) for TMP codes ---")
    
    cid = 3
    ctx = {'allowed_company_ids': [1, cid], 'active_test': False}
    
    # Search code like TMP
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'time', 'TMP'), ('company_ids', 'in', [cid])]], # Typo 'time' -> 'like' or 'ilike'
        # Wait, XMLRPC operator 'like' or 'ilike'
        # 'time' is wrong.
    ) 
    # Let's fix the query structure before writing
    pass

def run():
    print(f"--- Searching Dubai (ID 3) for TMP codes ---")
    cid = 3
    ctx = {'allowed_company_ids': [1, cid], 'active_test': False}
    
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'ilike', 'TMP'), ('company_ids', 'in', [cid])]],
        {'fields': ['id', 'name', 'code', 'active'], 'context': ctx})
        
    print(f"Found {len(accounts)} TMP accounts:")
    for a in accounts:
        print(f"  ID: {a['id']} | Code: {a['code']} | Name: {a['name']} | Active: {a['active']}")

if __name__ == "__main__":
    run()
