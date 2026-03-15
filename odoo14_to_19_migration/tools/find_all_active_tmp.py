import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def find_all_tmp():
    print(f"--- Searching Globally for TMP codes (Active & Inactive) ---")
    
    # Get all companies
    companies = models.execute_kw(db, uid, password, 'res.company', 'search', [[]])
    ctx = {'allowed_company_ids': companies, 'active_test': False}
    
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', 'ilike', 'TMP')]],
        {'fields': ['id', 'name', 'code', 'company_ids', 'active'], 'context': ctx})
        
    print(f"Found {len(accounts)} TMP accounts:")
    for a in accounts:
         print(f"  ID: {a['id']} | Code: {a['code']} | Name: {a['name']} | Companies: {a['company_ids']} | Active: {a['active']}")

if __name__ == "__main__":
    find_all_tmp()
