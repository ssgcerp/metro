import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

ALL_COMPANIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

def find_hidden():
    ctx = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    
    # Search ALL 104041 accounts with no filter
    accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '104041')]],
        {'fields': ['id', 'name', 'code', 'active', 'company_ids'], 'context': ctx})
    
    print(f"All 104041 accounts (no company filter): {len(accs)}")
    for a in accs:
        print(f"  ID {a['id']} | Active: {a['active']} | Companies: {a['company_ids']} | {a['name']}")

if __name__ == "__main__":
    find_hidden()
