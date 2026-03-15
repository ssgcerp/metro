import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def fix_rak_accounts():
    RAK_ID = 2
    
    # 1. Update the testing account 104041
    # We created ID 1760
    # Search just to be safe we target the right one
    rak_104041 = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '104041'), ('company_ids', 'in', [RAK_ID])]],
        {'fields': ['id', 'name']})
        
    if rak_104041:
        print(f"Updating VAT Input (ID {rak_104041[0]['id']})...")
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[rak_104041[0]['id']], {'name': 'VAT Input'}],
            {'context': {'allowed_company_ids': [RAK_ID]}})
    else:
        print("Error: RAK VAT Input 104041 not found (did test create fail?)")

    # 2. Create VAT Output 201017
    # Check if exists first
    rak_201017 = models.execute_kw(db, uid, password, 'account.account', 'search_count',
        [[('code', '=', '201017'), ('company_ids', 'in', [RAK_ID])]])
        
    if rak_201017 > 0:
        print("VAT Output 201017 already exists for RAK. Skipping.")
    else:
        # Get template from Good Account 201017 (Company 1)
        # We need to find it first.
        # Use company_ids = False or check all
        templ_201017 = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', '=', '201017')]],
            {'fields': ['name', 'account_type', 'reconcile', 'company_ids'], 'limit': 1})
            
        if templ_201017:
            print(f"Found template: {templ_201017[0]['name']}")
            vals = {
                'code': '201017',
                'name': 'VAT Output',
                'account_type': templ_201017[0]['account_type'],
                'reconcile': templ_201017[0]['reconcile'],
                'company_ids': [(6, 0, [RAK_ID])]
            }
            print(f"Creating VAT Output for RAK: {vals}")
            try:
                new_id = models.execute_kw(db, uid, password, 'account.account', 'create', 
                    [vals], 
                    {'context': {'allowed_company_ids': [RAK_ID]}})
                print(f"Success! Created VAT Output ID: {new_id}")
            except Exception as e:
                print(f"Error creating VAT Output: {e}")
        else:
            print("Error: Template VAT Output 201017 not found in other companies.")

if __name__ == "__main__":
    fix_rak_accounts()
