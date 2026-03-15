import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def search_lines():
    print(f"--- Searching Journal Lines for '201017C3TMP' ---")
    
    cid = 3
    ctx = {'allowed_company_ids': [1, cid]}
    
    # Search lines directly
    lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [['|', ('name', 'ilike', '201017C3TMP'), ('account_id.code', 'ilike', '201017C3TMP')]],
        {'fields': ['id', 'name', 'account_id', 'debit', 'credit'], 'limit': 10, 'context': ctx})
        
    print(f"Found {len(lines)} lines:")
    for l in lines:
        print(f"  Line ID: {l['id']} | Name: {l['name']} | Account: {l['account_id']}")

if __name__ == "__main__":
    search_lines()
