import xmlrpc.client
import ssl

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321" 

def main():
    context = ssl._create_unverified_context()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("Auth Failed")
        return

    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=context)
    
    # Target Code
    code = '104029'
    
    # 1. Standard Search
    args = [('code', '=', code)]
    print(f"Searching {args}...")
    try:
        res = models.execute_kw(db, uid, password, 'account.account', 'search_read', [args, ['code', 'name', 'company_ids']])
        print(f"Standard Result: {res}")
    except Exception as e:
        print(f"Standard Search Failed: {e}")
    
    # 2. Search with Context
    all_companies = models.execute_kw(db, uid, password, 'res.company', 'search', [[]])
    ctx = {'allowed_company_ids': all_companies, 'active_test': False, 'check_company': False}
    print(f"\nSearching with Context {ctx}...")
    try:
        res2 = models.execute_kw(db, uid, password, 'account.account', 'search_read', [args, ['code', 'name', 'company_ids']], {'context': ctx})
        print(f"Context Result: {res2}")
    except Exception as e:
        print(f"Context Search Failed: {e}")
    
    # 3. Search WITHOUT Code? List all active=False?
    print(f"\nSearching LIKE code...")
    args_like = [('code', 'ilike', code)]
    try:
        res3 = models.execute_kw(db, uid, password, 'account.account', 'search_read', [args_like, ['code', 'name', 'company_ids']], {'context': ctx})
        print(f"Like Result: {res3}")
    except Exception as e:
        print(f"Like Search Failed: {e}")

if __name__ == '__main__':
    main()
