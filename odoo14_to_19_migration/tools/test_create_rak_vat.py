import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def test_create():
    RAK_ID = 2
    
    # Try creating 104041 for RAK
    # Need to know the type/internal_group
    # Let's read the Good Account (40) first to copy basic fields
    
    acc_templ = models.execute_kw(db, uid, password, 'account.account', 'read',
        [[40]],
        {'fields': ['name', 'account_type', 'internal_group', 'reconcile']})
    
    if not acc_templ:
        print("Template account 40 not found.")
        return
        
    vals = {
        'code': '104041',
        'name': 'VAT Input (RAK Test)',
        'account_type': acc_templ[0]['account_type'],
        'reconcile': acc_templ[0]['reconcile'],
        # Use company_ids for Odoo 19 Enterprise (Shared Accounts)
        'company_ids': [(6, 0, [RAK_ID])]
    }
    
    print(f"Attempting to create account for RAK: {vals}")
    
    try:
        # pass allowed_company_ids
        ctx = {'allowed_company_ids': [RAK_ID]}
        new_id = models.execute_kw(db, uid, password, 'account.account', 'create', [vals], {'context': ctx})
        print(f"Success! Created Account ID: {new_id}")
    except Exception as e:
        print(f"Error creating account: {e}")

if __name__ == "__main__":
    test_create()
