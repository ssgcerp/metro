import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_dubai():
    print(f"--- Debugging Dubai (ID 3) VAT Accounts ---")
    
    cid = 3
    ctx = {'allowed_company_ids': [1, cid]}
    
    # 1. Search all 104041 variations
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'like', '104041'), ('company_ids', 'in', [cid])]],
        {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
        
    print(f"Found {len(accounts)} accounts matching '104041':")
    for a in accounts:
        print(f"  ID: {a['id']} | Code: {a['code']} | Name: {a['name']}")
        
    # 2. Try to rename '104041C3TMP' to '104041'
    tmp_acc = next((a for a in accounts if 'TMP' in a['code']), None)
    if tmp_acc:
        print(f"Attempting to rename ID {tmp_acc['id']} to '104041'...")
        try:
            models.execute_kw(db, uid, password, 'account.account', 'write',
                [[tmp_acc['id']], {'code': '104041'}],
                {'context': ctx})
            print("  Success!")
        except Exception as e:
            print(f"  Failed: {e}")
            
    # Check if 104041 exists specifically
    exact = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '104041'), ('company_ids', 'in', [cid])]],
        {'fields': ['id', 'name'], 'context': ctx})
    if exact:
        print(f"EXACT MATCH for 104041 found: {exact}")

if __name__ == "__main__":
    debug_dubai()
