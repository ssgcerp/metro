import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_rak_vat():
    print("Connecting to Odoo...")
    
    # 1. Find Company "RAS AL KHAIMAH"
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read',
        [[('name', 'ilike', 'RAK')]], # RAK is common abbr
        {'fields': ['id', 'name']})
        
    rak_id = None
    if not companies:
         # Try full name
        companies = models.execute_kw(db, uid, password, 'res.company', 'search_read',
            [[('name', 'ilike', 'RAS AL KHAIMAH')]],
            {'fields': ['id', 'name']})
            
    if not companies:
        print("Error: Could not find company matches for 'RAK' or 'RAS AL KHAIMAH'")
        # List all to be sure
        all_comps = models.execute_kw(db, uid, password, 'res.company', 'search_read', [], {'fields': ['id', 'name']})
        print("Available Companies:", all_comps)
        return

    print(f"Found Companies matching RAK: {companies}")
    # Assume first one or let user pick if multiple? 
    # Usually specificity matters.
    for c in companies:
        if 'RAS AL KHAIMAH' in c['name'] or 'RAK' in c['name']:
            rak_id = c['id']
            print(f"Selected Target Company: {c['name']} (ID: {rak_id})")
            break
            
    if not rak_id:
        print("Could not obtain a single RAK ID.")
        return

    print(f"\n--- Searching for FIRST 20 accounts in RAK (ID {rak_id}) ---")
    # Just list any accounts to see what's there
    rak_accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [['|', ('company_ids', 'in', [rak_id]), ('company_ids', '=', False)]],
        {'fields': ['id', 'name', 'code', 'company_ids'], 'limit': 20})
        
    if not rak_accounts:
        print("No accounts found AT ALL for RAK. Chart of Accounts might be missing.")
    
    for acc in rak_accounts:
        print(f" - Found: [{acc['code']}] {acc['name']} (IDs: {acc['company_ids']})")

if __name__ == "__main__":
    debug_rak_vat()
