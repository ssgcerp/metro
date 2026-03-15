import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def deep_search():
    string = "201017C3TMP"
    print(f"--- Deep Search for '{string}' ---")
    
    # Check Accounts
    accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [['|', ('code', 'ilike', string), ('name', 'ilike', string)]],
        {'fields': ['id', 'name', 'code', 'company_ids']})
    print(f"Accounts found: {len(accs)}")
    for a in accs: print(f"  ACC: {a}")
        
    # Check Taxes
    taxes = models.execute_kw(db, uid, password, 'account.tax', 'search_read',
        [[('name', 'ilike', string)]],
        {'fields': ['id', 'name', 'company_id']})
    print(f"Taxes found: {len(taxes)}")
    for t in taxes: print(f"  TAX: {t}")
        
    # Check Journals
    journals = models.execute_kw(db, uid, password, 'account.journal', 'search_read',
        [['|', ('name', 'ilike', string), ('code', 'ilike', string)]],
        {'fields': ['id', 'name', 'code', 'company_id']})
    print(f"Journals found: {len(journals)}")
    for j in journals: print(f"  JRN: {j}")

if __name__ == "__main__":
    deep_search()
