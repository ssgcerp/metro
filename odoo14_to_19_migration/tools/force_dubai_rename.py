import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def force_rename():
    print(f"--- Forcing Rename for Dubai VAT Output (ID 1802) ---")
    
    cid = 3
    ctx = {'allowed_company_ids': [1, cid]}
    
    # 1. Read before
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[1802], ['name', 'code']], {'context': ctx})
    print(f"Before: {acc}")
    
    # 2. Write
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[1802], {'name': 'VAT Output', 'code': '201017'}],
            {'context': ctx})
        print("Write successful.")
    except Exception as e:
        print(f"Write failed: {e}")
        
    # 3. Read after
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[1802], ['name', 'code']], {'context': ctx})
    print(f"After: {acc}")

if __name__ == "__main__":
    force_rename()
