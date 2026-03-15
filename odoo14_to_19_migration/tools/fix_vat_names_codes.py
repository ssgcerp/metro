import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def fix_tmp_names():
    print(f"--- Fixing TMP Account Names in {db} ---")
    
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})
    
    for c in companies:
        cid = c['id']
        cname = c['name']
        print(f"\nProcessing [{cid}] {cname}...")
        
        ctx = {'allowed_company_ids': [1, cid]}
        
        # Determine Suffix
        suffix = cname.split(' ')[0].upper()[:3]
        if 'DUBAI' in cname.upper(): suffix = 'DXB'
        elif 'SHARJAH' in cname.upper(): suffix = 'SHJ'
        elif 'RAS AL KHAIMAH' in cname.upper(): suffix = 'RAK'
        elif 'AJMAN' in cname.upper(): suffix = 'AJM'
        elif 'MYSORE' in cname.upper(): suffix = 'MYS'
        elif 'ABU DHABI' in cname.upper(): suffix = 'AUH'
        
        # FIND AND FIX INPUT
        # Search for accounts with TMP in code OR mismatch names
        # Actually just find the account we created if possible
        # Or search by code '104041%'
        
        vat_in = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', 'like', '104041'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
            
        for acc in vat_in:
            current_code = acc['code']
            current_name = acc['name']
            
            # Is it ugly?
            if 'TMP' in current_code:
                print(f"  Fixing Input: {current_code} {current_name}")
                
                # 1. Try generic code 104041
                try:
                    models.execute_kw(db, uid, password, 'account.account', 'write', [[acc['id']], {'code': '104041'}], {'context': ctx})
                    print("  -> Set code to 104041")
                except Exception as e:
                    print(f"  -> 104041 taken/invalid. Using suffix.")
                    new_code = f"104041-{suffix}"
                    try:
                         models.execute_kw(db, uid, password, 'account.account', 'write', [[acc['id']], {'code': new_code}], {'context': ctx})
                         print(f"  -> Set code to {new_code}")
                    except Exception as e2:
                        print(f"  -> Failed to set code {new_code}: {e2}")

            # Always update name if requested
            desired_name = f"VAT Input ({cname})"
            if current_name != desired_name:
                models.execute_kw(db, uid, password, 'account.account', 'write', [[acc['id']], {'name': desired_name}], {'context': ctx})
                print(f"  -> Updated name to '{desired_name}'")

        # FIND AND FIX OUTPUT
        vat_out = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', 'like', '201017'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
            
        for acc in vat_out:
            current_code = acc['code']
            current_name = acc['name']
            
            # Is it ugly?
            if 'TMP' in current_code:
                print(f"  Fixing Output: {current_code} {current_name}")
                
                # 1. Try generic code 201017
                try:
                    models.execute_kw(db, uid, password, 'account.account', 'write', [[acc['id']], {'code': '201017'}], {'context': ctx})
                    print("  -> Set code to 201017")
                except Exception as e:
                    print(f"  -> 201017 taken/invalid. Using suffix.")
                    new_code = f"201017-{suffix}"
                    try:
                         models.execute_kw(db, uid, password, 'account.account', 'write', [[acc['id']], {'code': new_code}], {'context': ctx})
                         print(f"  -> Set code to {new_code}")
                    except Exception as e2:
                        print(f"  -> Failed to set code {new_code}: {e2}")

            # Always update name if requested
            desired_name = f"VAT Output ({cname})"
            if current_name != desired_name:
                models.execute_kw(db, uid, password, 'account.account', 'write', [[acc['id']], {'name': desired_name}], {'context': ctx})
                print(f"  -> Updated name to '{desired_name}'")

if __name__ == "__main__":
    fix_tmp_names()
