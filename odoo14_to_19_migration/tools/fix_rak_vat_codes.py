import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def fix_codes():
    ctx = {'allowed_company_ids': [1, 2]}
    RAK_ID = 2
    
    print("--- Fixing ID 1760 (VAT Input) ---")
    try:
        # Check current state first
        acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[1760], ['code']], {'context': ctx})
        print(f"Current Code: {acc[0]['code']}")
        
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[1760], {'code': '104041', 'name': 'VAT Input'}],
            {'context': ctx})
        print("Success: Updated ID 1760 code to 104041")
    except Exception as e:
        print(f"Error updating 1760: {e}")

    print("\n--- Fixing ID 1761 (VAT Output) ---")
    try:
        # Check current state first
        acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[1761], ['code']], {'context': ctx})
        print(f"Current Code: {acc[0]['code']}")

        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[1761], {'code': '201017', 'name': 'VAT Output'}],
            {'context': ctx})
        print("Success: Updated ID 1761 code to 201017")
    except Exception as e:
        print(f"Error updating 1761: {e}")

if __name__ == "__main__":
    fix_codes()
