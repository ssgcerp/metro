import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def fix_dubai_final():
    print(f"--- Force Fixing Dubai (ID 3) VAT Output ---")
    
    # 1. Identify the Good Account (Should be 1802)
    # We search by company_ids = 3 and active=True/False
    ctx = {'allowed_company_ids': [1, 3], 'active_test': False}
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('company_ids', 'in', [3])]], 
        {'fields': ['id', 'name', 'code', 'company_ids', 'active'], 'context': ctx})
        
    good_account_id = None
    duplicates = []
    
    for a in accounts:
        # Check if it matches our target
        is_target = False
        if '201017' in str(a['code']) or 'VAT Output' in a['name']:
            is_target = True
        
        if is_target:
            if a['code'] == '201017' and a['name'] == 'VAT Output' and a['active'] == True:
                if not good_account_id:
                    good_account_id = a['id']
                    print(f"  Found Good Account: {a}")
                else:
                    duplicates.append(a)
            else:
                duplicates.append(a)
                
    print(f"  Good Account ID: {good_account_id}")
    print(f"  Duplicates to cleaning: {len(duplicates)}")
    
    # 2. Fix Duplicates
    for d in duplicates:
        print(f"    Cleaning Duplicate: {d}")
        # Rename code to OLD to hide it
        new_code = f"{d['code']}_OLD_{d['id']}" if d['code'] else f"OLD_{d['id']}"
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[d['id']], {'active': False, 'code': new_code}],
            {'context': ctx})
            
    # 3. Force Update Good Account (Trigger cache invalidation hopefully)
    if good_account_id:
        print(f"    Force Updating Good Account {good_account_id}...")
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[good_account_id], {'name': 'VAT Output', 'code': '201017'}],
            {'context': ctx})
            
    print("--- Done ---")

if __name__ == "__main__":
    fix_dubai_final()
