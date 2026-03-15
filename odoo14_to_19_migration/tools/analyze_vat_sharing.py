import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def analyze_sharing():
    # RAK ID is 2 (from previous output)
    RAK_ID = 2
    
    codes = ['104041', '201017']
    print(f"Checking sharing settings for {codes}...")
    
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'in', codes)]],
        {'fields': ['id', 'name', 'code', 'company_ids']})
        
    for acc in accounts:
        comp_ids = acc.get('company_ids', [])
        print(f"\nAccount [{acc['code']}] {acc['name']}")
        print(f" - ID: {acc['id']}")
        print(f" - Company IDs: {comp_ids}")
        
        if RAK_ID in comp_ids:
            print(" - STATUS: Shared with RAK (OK)")
        else:
            print(" - STATUS: NOT shared with RAK (MISSING)")
            print("   -> Needs to be added.")

if __name__ == "__main__":
    analyze_sharing()
