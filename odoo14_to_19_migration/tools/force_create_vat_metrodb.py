import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def force_create_vat_input():
    print(f"Force Creating VAT Input in {db} for RAK (ID 2)...")
    RAK_ID = 2
    ctx = {'allowed_company_ids': [1, RAK_ID]}
    
    # 1. Get Template
    templ = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '104041')]],
        {'fields': ['account_type', 'reconcile'], 'limit': 1, 'context': ctx})
        
    if not templ:
        print("Template 104041 not found!")
        return

    # 2. Create with valid alphanumeric temp code
    temp_code = '104041RAK'
    vals = {
        'code': temp_code, 
        'name': 'VAT Input',
        'account_type': templ[0]['account_type'],
        'reconcile': templ[0]['reconcile'],
        'company_ids': [(6, 0, [RAK_ID])]
    }
    
    try:
        new_id = models.execute_kw(db, uid, password, 'account.account', 'create', [vals], {'context': ctx})
        print(f"Success! Created ID: {new_id} with code=False")
        
        # 3. Update to correct code
        print("Updating to real code 104041...")
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[new_id], {'code': '104041'}],
            {'context': ctx})
        print("Success! Code updated.")
        
    except Exception as e:
        print(f"Error: {e}")
        # If it failed, try searching if we made a mess
        
if __name__ == "__main__":
    force_create_vat_input()
