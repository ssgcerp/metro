import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def inspect_rak():
    print(f"--- Inspecting RAK (ID 2) VAT Accounts ---")
    
    cid = 2
    ctx = {'allowed_company_ids': [1, cid]}
    
    # Search all 104041 variations
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'like', '104041'), ('company_ids', 'in', [cid])]],
        {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
        
    print(f"Found {len(accounts)} accounts matching '104041':")
    for a in accounts:
        print(f"  ID: {a['id']} | Code: {a['code']} | Name: {a['name']} | Companies: {a['company_ids']}")

    # Check for Journal Items on these accounts
    for a in accounts:
        count = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id', '=', a['id']), ('company_id', '=', cid)]],
            {'context': ctx})
        print(f"  -> Account {a['id']} has {count} journal items for RAK.")

if __name__ == "__main__":
    inspect_rak()
