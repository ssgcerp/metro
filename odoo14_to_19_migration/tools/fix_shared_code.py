import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def fix_744():
    print(f"--- Fixing Code for Shared Account 744 ---")
    
    # Use master context
    ctx = {'allowed_company_ids': [1, 2, 3, 5, 8]}
    
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[744], {'code': '104041', 'name': 'VAT Input'}],
            {'context': ctx})
        print("Success! Code set to 104041.")
    except Exception as e:
        print(f"Error setting code: {e}")
        
    # Verify
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', 
        [[744], ['id', 'name', 'code', 'company_ids']],
        {'context': ctx})
    print(f"Final State: {acc}")

if __name__ == "__main__":
    fix_744()
