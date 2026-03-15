import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_744():
    print(f"--- Debugging ID 744 ---")
    
    # Check as superset context
    ctx = {'allowed_company_ids': [1, 2, 3, 5, 8]}
    
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', 
        [[744], ['id', 'name', 'code', 'company_ids', 'active']],
        {'context': ctx})
        
    print(f"Account 744: {acc}")
    
    # Check searching it from RAK context
    ctx_rak = {'allowed_company_ids': [1, 2]}
    found = models.execute_kw(db, uid, password, 'account.account', 'search_count',
        [[('id', '=', 744)]], {'context': ctx_rak})
    print(f"Visible from RAK? {found}")

if __name__ == "__main__":
    debug_744()
