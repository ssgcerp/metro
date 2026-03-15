import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_detailed():
    RAK_ID = 2
    ctx = {'allowed_company_ids': [1, RAK_ID]}
    
    print("--- Detailed search for 'VAT' lines on wrong accounts ---")
    
    # Exclude the new VAT accounts we just created
    new_vat_ids = [1764, 1761]
    
    lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [[('company_id', '=', RAK_ID), ('name', 'ilike', 'VAT'), ('account_id', 'not in', new_vat_ids)]],
        {'fields': ['id', 'name', 'account_id', 'debit', 'credit', 'move_id', 'date'], 'limit': 50, 'context': ctx})
        
    for l in lines:
        acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[l['account_id'][0]], ['code', 'name']], {'context': ctx})[0]
        print(f"Line ID describe: {l['id']}")
        print(f" - Move: {l['move_id'][1]}")
        print(f" - Date: {l['date']}")
        print(f" - Desc: {l['name']}")
        print(f" - Amount: Debit {l['debit']} | Credit {l['credit']}")
        print(f" - CURRENT Account: [{acc['code']}] {acc['name']}")
        print("-" * 30)

if __name__ == "__main__":
    debug_detailed()
