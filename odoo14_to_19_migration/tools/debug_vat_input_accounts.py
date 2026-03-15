import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_vat_accounts():
    print("Searching for accounts with 'VAT Input' in name...")
    
    # Search for accounts
    # Search for accounts with 'VAT Input' in name
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [['|', ('name', '=', 'VAT Input'), ('code', '=', False)]],
        {'fields': ['id', 'code', 'name', 'currency_id']})
        
    print(f"Found {len(accounts)} potential accounts:")
    for acc in accounts:
        # Filter noise: Must have 'VAT Input' in name.
        if 'VAT Input' not in acc['name']:
            continue
            
        print(f"ID: {acc['id']}, Code: {acc['code']}, Name: {acc['name']}")
        
        # Count move lines for this account
        count = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id', '=', acc['id'])]])
        print(f"  -> Associated Journal Items: {count}")
        
    # Also check if there are lines with 'VAT Input' as label but maybe weird account?
    # The user screenshot showed report lines. 
    # '104041 VAT Input' -> standard account.
    # 'VAT Input' -> Could be an account without code?
    
    accounts_no_code = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('name', 'ilike', 'VAT Input'), ('code', '=', False)]],
        {'fields': ['id', 'code', 'name']})
        
    if accounts_no_code:
        print("\nAccounts without code:")
        for acc in accounts_no_code:
            print(f"ID: {acc['id']}, Name: {acc['name']}")

if __name__ == "__main__":
    debug_vat_accounts()
