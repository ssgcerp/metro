import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def search_all_companies():
    print(f"--- Searching Globally for 201017% ---")
    
    # Get all companies
    companies = models.execute_kw(db, uid, password, 'res.company', 'search', [[]])
    ctx = {'allowed_company_ids': companies, 'active_test': False}
    
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [['|', ('code', 'like', '201017%'), ('name', 'ilike', 'VAT Output')]],
        {'fields': ['id', 'name', 'code', 'company_ids', 'active'], 'context': ctx})
        
    print(f"Found {len(accounts)} accounts globally:")
    for a in accounts:
         print(f"  ID: {a['id']} | Code: {a['code']} | Name: {a['name']}")
         print(f"    Companies: {a['company_ids']}")
         print(f"    Active: {a['active']}")

if __name__ == "__main__":
    search_all_companies()
