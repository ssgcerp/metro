import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def inspect_candidates():
    print(f"--- Inspecting VAT Output Candidates ---")
    
    # Check ID 70 and 1761
    ctx = {'allowed_company_ids': [1, 2, 3, 5, 8]}
    
    candidates = [70, 1761]
    
    for cid in candidates:
        acc = models.execute_kw(db, uid, password, 'account.account', 'read', 
            [[cid], ['id', 'name', 'code', 'company_ids']],
            {'context': ctx})
        if acc:
            print(f"ID {cid}: {acc}")
        else:
            print(f"ID {cid} not found or inaccessible.")

if __name__ == "__main__":
    inspect_candidates()
