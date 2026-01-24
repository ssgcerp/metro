
import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Get all journals
    journals = models.execute_kw(db, uid, password, 'account.journal', 'search_read', 
        [[]], 
        {'fields': ['name', 'company_id', 'type', 'code']})
    
    # Group by Company
    grouped = {}
    for j in journals:
        comp_name = j['company_id'][1]
        if comp_name not in grouped:
            grouped[comp_name] = []
        grouped[comp_name].append(j)
        
    for comp in sorted(grouped.keys()):
        print(f"\n--- {comp} ---")
        for j in grouped[comp]:
            print(f"  [{j['type']}] {j['name']} (Code: {j['code']})")
            
except Exception as e:
    print(f"Error: {e}")
