import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def fix_sharing():
    RAK_ID = 2
    codes = ['104041', '201017']
    
    # 1. Fetch Accounts
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'in', codes)]],
        {'fields': ['id', 'name', 'code', 'company_ids']})
        
    for acc in accounts:
        print(f"Processing Account {acc['code']} {acc['name']}...")
        current_ids = acc.get('company_ids', [])
        print(f" - Current IDs: {current_ids}")
        
        if RAK_ID in current_ids:
            print(" - Already shared with RAK. Skipping.")
        else:
            new_ids = current_ids + [RAK_ID]
            # Use [(6, 0, ids)] for Many2many write
            # Actually, standard write with list of IDs usually works for M2M in newer Odoo,
            # but (6,0,ids) is safer.
            
            print(f" - Adding RAK ID {RAK_ID}... New List: {new_ids}")
            try:
                # pass allowed_company_ids to avoid multi-company rule issues
                ctx = {'allowed_company_ids': new_ids}
                models.execute_kw(db, uid, password, 'account.account', 'write',
                    [[acc['id']], {'company_ids': [(6, 0, new_ids)]}],
                    {'context': ctx})
                print(" - Success!")
            except Exception as e:
                print(f" - Error writing: {e}")

    # Verify
    print("\n--- Verification ---")
    accounts_verify = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'in', codes)]],
        {'fields': ['id', 'name', 'code', 'company_ids']})
    for acc in accounts_verify:
        print(f"Account {acc['code']}: {acc['company_ids']}")

if __name__ == "__main__":
    fix_sharing()
