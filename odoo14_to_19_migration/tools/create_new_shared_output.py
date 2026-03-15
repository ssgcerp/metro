import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def create_shared():
    print(f"--- Creating New Shared VAT Output Account ---")
    
    target_companies = [2, 3, 5, 8]
    ctx = {'allowed_company_ids': [1, 2, 3, 5, 8]}
    
    vals = {
        'code': '201017',
        'name': 'VAT Output',
        'account_type': 'liability_current', # Correct type for VAT Output?
        'company_ids': [(6, 0, target_companies)]
    }
    
    # Try different codes if 201017 is taken
    # But theoretically it's free in 3, 5, 8 (checked) and 2 (we will rename 1761 if needed)
    
    # First, must rename 1761 in Company 2 to free up the code!
    print("Renaming existing RAK account 1761 to avoid conflict...")
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[1761], {'code': '201017RAKOLD'}],
            {'context': {'allowed_company_ids': [1, 2]}})
        print("Renamed 1761.")
    except Exception as e:
        print(f"Error renaming 1761: {e}")

    print("Creating new account...")
    try:
        new_id = models.execute_kw(db, uid, password, 'account.account', 'create',
            [vals], {'context': ctx})
        print(f"Success! Created Account ID {new_id}")
    except Exception as e:
        print(f"Creation Failed: {e}")

if __name__ == "__main__":
    create_shared()
