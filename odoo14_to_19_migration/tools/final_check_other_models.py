import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def safe_search(model, domain, fields):
    print(f"  Searching {model}...")
    try:
        res = models.execute_kw(db, uid, password, model, 'search_read', [domain], {'fields': fields, 'limit': 10})
        if res:
            print(f"    FOUND in {model}: {res}")
        else:
            print(f"    No matches in {model}.")
    except Exception as e:
        print(f"    Error searching {model}: {e}")

def final_check():
    string = "C3TMP"
    print(f"--- Robust Search for '{string}' ---")
    
    # 1. Account Group
    safe_search('account.group', ['|', ('name', 'ilike', string), ('code_prefix_start', 'ilike', string)], ['id', 'name', 'code_prefix_start'])
    
    # 2. Partner
    safe_search('res.partner', ['|', ('name', 'ilike', string), ('ref', 'ilike', string)], ['id', 'name', 'ref'])
    
    # 3. Analytic
    safe_search('account.analytic.account', ['|', ('name', 'ilike', string), ('code', 'ilike', string)], ['id', 'name', 'code'])
    
    # 4. Tax Group
    safe_search('account.tax.group', [('name', 'ilike', string)], ['id', 'name'])
    
    # 5. Company
    safe_search('res.company', [('name', 'ilike', string)], ['id', 'name'])
    
    # 6. Account (Name Only - safest)
    safe_search('account.account', [('name', 'ilike', string)], ['id', 'name', 'code'])
    
    # 7. Account (Code Only - safest)
    safe_search('account.account', [('code', 'ilike', string)], ['id', 'name', 'code'])

if __name__ == "__main__":
    final_check()
