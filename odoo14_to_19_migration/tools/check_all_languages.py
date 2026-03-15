import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def check_langs():
    print(f"--- Checking Account 1802 in All Languages ---")
    
    # 1. Get Active Languages
    langs = models.execute_kw(db, uid, password, 'res.lang', 'search_read',
        [], {'fields': ['code', 'name']})
        
    print(f"Active Languages: {len(langs)}")
    
    # 2. Check Account 1802 in each lang
    cid = 3
    base_ctx = {'allowed_company_ids': [1, cid]}
    
    for l in langs:
        code = l['code']
        ctx = base_ctx.copy()
        ctx['lang'] = code
        
        acc = models.execute_kw(db, uid, password, 'account.account', 'read',
            [[1802]], {'fields': ['name', 'code'], 'context': ctx})
            
        print(f"[{code}] {l['name']}: {acc[0]['name']} | {acc[0]['code']}")
        
        # 3. Fix if wrong
        if 'TMP' in acc[0]['name'] or '201017' not in acc[0]['code']:
             print(f"  -> FIXING for {code}...")
             models.execute_kw(db, uid, password, 'account.account', 'write',
                [[1802], {'name': 'VAT Output', 'code': '201017'}],
                {'context': ctx})
             print("  -> Done.")

if __name__ == "__main__":
    check_langs()
