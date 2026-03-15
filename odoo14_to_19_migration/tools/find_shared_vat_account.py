import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def find_shared():
    print(f"--- Searching for SHARED VAT Output (By Name) ---")
    
    companies = models.execute_kw(db, uid, password, 'res.company', 'search', [[]])
    ctx = {'allowed_company_ids': companies} 
    
    # Search by Name
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('name', 'ilike', 'VAT Output')]],
        {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
        
    found_any = False
    for a in accounts:
        if len(a['company_ids']) > 1:
            print(f"FOUND SHARED: ID {a['id']} | Code: {a['code']} | Name: {a['name']}")
            print(f"  Companies: {a['company_ids']}")
            found_any = True
            
    if not found_any:
        print("No shared account found by name 'VAT Output'.")
        
    print("\n--- Inspecting specific candidates ---")
    # Check if we can find one that looks like the partner to 744 (Companies=[5,3,8,2])
    for a in accounts:
        if 5 in a['company_ids'] or 3 in a['company_ids']:
             print(f"Candidate? ID {a['id']} | Code: {a['code']} | Companies: {a['company_ids']}")

if __name__ == "__main__":
    find_shared()
