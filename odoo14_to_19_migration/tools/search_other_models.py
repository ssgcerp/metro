import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def search_others():
    string = "201017C3TMP"
    print(f"--- Searching Other Models for '{string}' ---")
    
    # 1. Account Group
    groups = models.execute_kw(db, uid, password, 'account.group', 'search_read',
        [['|', ('name', 'ilike', string), ('code_prefix_start', 'ilike', string)]],
        {'fields': ['id', 'name', 'code_prefix_start']})
    print(f"Account Groups: {len(groups)}")
    for g in groups: print(f"  GROUP: {g}")
        
    # 2. Partner (maybe name or ref)
    partners = models.execute_kw(db, uid, password, 'res.partner', 'search_read',
        [['|', ('name', 'ilike', string), ('ref', 'ilike', string)]],
        {'fields': ['id', 'name', 'ref']})
    print(f"Partners: {len(partners)}")
    for p in partners: print(f"  PARTNER: {p}")
        
    # 3. Analytic Account
    analytics = models.execute_kw(db, uid, password, 'account.analytic.account', 'search_read',
        [['|', ('name', 'ilike', string), ('code', 'ilike', string)]],
        {'fields': ['id', 'name', 'code']})
    print(f"Analytic Accounts: {len(analytics)}")
    for a in analytics: print(f"  ANALYTIC: {a}")
    
    # 4. Check if Account Code has hidden chars
    # Get ID 1802 and print repr(code)
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[1802], ['code']], {'context': {'allowed_company_ids': [1, 3]}})
    print(f"Account 1802 Code Repr: {repr(acc[0]['code'])}")

if __name__ == "__main__":
    search_others()
