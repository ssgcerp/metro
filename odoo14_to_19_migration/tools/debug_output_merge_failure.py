import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_failure():
    print(f"--- Debugging VAT Output Merge Failure ---")
    
    MASTER_ID = 1761
    
    # 1. Check Master state
    ctx_master = {'allowed_company_ids': [1, 2]}
    master = models.execute_kw(db, uid, password, 'account.account', 'read', [[MASTER_ID], ['code', 'name', 'company_ids']], {'context': ctx_master})
    print(f"Master (1761): {master}")
    
    # 2. Check Duplicates in Dubai (3)
    ctx_dubai = {'allowed_company_ids': [1, 3]}
    dups = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('name', 'ilike', 'VAT Output'), ('company_ids', 'in', [3])]],
        {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx_dubai})
    print(f"Dubai Duplicates: {dups}")
    
    # 3. Try appending Company 3 to Master
    print("\nAttempting to add Company 3 to Master 1761...")
    try:
        # Just write company_ids, don't touch code
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[MASTER_ID], {'company_ids': [(4, 3)]}], # 4 = Link
            {'context': {'allowed_company_ids': [1, 2, 3]}})
        print("Success! Added Company 3.")
    except Exception as e:
        print(f"Failed to add Company 3: {e}")

if __name__ == "__main__":
    debug_failure()
