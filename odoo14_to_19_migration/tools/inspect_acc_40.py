import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def inspect_40():
    print(f"--- Inspecting Account ID 40 ---")
    
    # Use context of company 1 to find it? Or default?
    ctx = {'allowed_company_ids': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
    
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', 
        [[40], ['id', 'name', 'code', 'company_ids']],
        {'context': ctx})
        
    if acc:
        print(f"ID 40 Details: {acc}")
    else:
        print("ID 40 not found or not accessible.")

if __name__ == "__main__":
    inspect_40()
