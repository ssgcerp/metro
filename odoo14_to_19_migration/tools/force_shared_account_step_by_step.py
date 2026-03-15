import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def force_shared_step():
    print(f"--- Forcing Shared Account Step-by-Step ---")
    
    MASTER_ID = 1761
    
    # 1. Rename back to 201017 for Company 2
    # Ensure current state is clean
    print("Renaming 1761 back to 201017...")
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[MASTER_ID], {'code': '201017', 'name': 'VAT Output'}],
            {'context': {'allowed_company_ids': [1, 2]}})
        print("Success.")
    except Exception as e:
        print(f"Error restoring name: {e}")
        
    # 2. Add Company 3
    print("Adding Company 3...")
    try:
        # Pass code explicitly
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[MASTER_ID], {'company_ids': [(4, 3)], 'code': '201017'}],
            {'context': {'allowed_company_ids': [1, 2, 3]}})
        print("Success! Added Company 3.")
    except Exception as e:
        print(f"Failed to add Company 3: {e}")
        
    # 3. Add Company 5
    print("Adding Company 5...")
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[MASTER_ID], {'company_ids': [(4, 5)], 'code': '201017'}],
            {'context': {'allowed_company_ids': [1, 2, 3, 5]}})
        print("Success! Added Company 5.")
    except Exception as e:
        print(f"Failed to add Company 5: {e}")

    # 4. Add Company 8
    print("Adding Company 8...")
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[MASTER_ID], {'company_ids': [(4, 8)], 'code': '201017'}],
            {'context': {'allowed_company_ids': [1, 2, 3, 5, 8]}})
        print("Success! Added Company 8.")
    except Exception as e:
        print(f"Failed to add Company 8: {e}")

if __name__ == "__main__":
    force_shared_step()
