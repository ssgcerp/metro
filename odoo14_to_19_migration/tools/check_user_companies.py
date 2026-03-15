import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def check_access():
    print(f"--- Checking Access for User {uid} ---")
    user = models.execute_kw(db, uid, password, 'res.users', 'read', 
        [uid], {'fields': ['name', 'company_ids', 'company_id']})
    
    print(f"User: {user[0]['name']}")
    print(f"Current Company: {user[0]['company_id']}")
    print(f"Allowed Companies: {user[0]['company_ids']}")
    
    # List all companies
    all_comps = models.execute_kw(db, uid, password, 'res.company', 'search', [[]])
    print(f"All Company IDs in DB: {all_comps}")
    
    missing = set(all_comps) - set(user[0]['company_ids'])
    if missing:
        print(f"MISSING ACCESS TO: {missing}")
        print("Adding access...")
        try:
            models.execute_kw(db, uid, password, 'res.users', 'write',
                [[uid], {'company_ids': [(4, c) for c in missing]}])
            print("Access granted to all companies.")
        except Exception as e:
            print(f"Error granting access: {e}")
    else:
        print("User has access to all companies.")

if __name__ == "__main__":
    check_access()
