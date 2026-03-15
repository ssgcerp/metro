import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"  # TARGET CORRECT DB
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def fix_metrodb():
    print(f"Applying VAT fix to DB: {db}")
    RAK_ID = 2
    ctx = {'allowed_company_ids': [1, RAK_ID]}
    
    # 1. Create/Find VAT Input 104041 for RAK
    # Check if exists (by code or name+company)
    vat_in = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '104041'), ('company_ids', 'in', [RAK_ID])]],
        {'fields': ['id', 'name'], 'context': ctx})
        
    if vat_in:
        print(f"VAT Input 104041 already exists: {vat_in}")
    else:
        # Create it
        print("Creating VAT Input for RAK...")
        # Get template
        templ_in = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', '=', '104041')]],
            {'fields': ['account_type', 'reconcile'], 'limit': 1, 'context': ctx})
            
        if templ_in:
            vals = {
                'code': '104041',
                'name': 'VAT Input',
                'account_type': templ_in[0]['account_type'],
                'reconcile': templ_in[0]['reconcile'],
                'company_ids': [(6, 0, [RAK_ID])]
            }
            try:
                new_id = models.execute_kw(db, uid, password, 'account.account', 'create', [vals], {'context': ctx})
                print(f"Success! Created VAT Input ID: {new_id}")
                
                # Verify Code
                acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[new_id], ['code']], {'context': ctx})
                if not acc[0]['code']:
                    print("Code missing! Applying fix...")
                    models.execute_kw(db, uid, password, 'account.account', 'write', [[new_id], {'code': '104041'}], {'context': ctx})
                    print("Code fixed.")
            except Exception as e:
                print(f"Error create VAT Input: {e}")
        else:
            print("Error: Template VAT Input 104041 not found in any company!")

    # 2. Create/Find VAT Output 201017 for RAK
    vat_out = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '201017'), ('company_ids', 'in', [RAK_ID])]],
        {'fields': ['id', 'name'], 'context': ctx})
        
    if vat_out:
        print(f"VAT Output 201017 already exists: {vat_out}")
    else:
        # Create it
        print("Creating VAT Output for RAK...")
        templ_out = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', '=', '201017')]],
            {'fields': ['account_type', 'reconcile'], 'limit': 1, 'context': ctx})
            
        if templ_out:
            vals = {
                'code': '201017',
                'name': 'VAT Output',
                'account_type': templ_out[0]['account_type'],
                'reconcile': templ_out[0]['reconcile'],
                'company_ids': [(6, 0, [RAK_ID])]
            }
            try:
                new_id = models.execute_kw(db, uid, password, 'account.account', 'create', [vals], {'context': ctx})
                print(f"Success! Created VAT Output ID: {new_id}")
                
                 # Verify Code
                acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[new_id], ['code']], {'context': ctx})
                if not acc[0]['code']:
                    print("Code missing! Applying fix...")
                    models.execute_kw(db, uid, password, 'account.account', 'write', [[new_id], {'code': '201017'}], {'context': ctx})
                    print("Code fixed.")
            except Exception as e:
                 print(f"Error create VAT Output: {e}")
        else:
             print("Error: Template VAT Output 201017 not found in any company!")

if __name__ == "__main__":
    fix_metrodb()
