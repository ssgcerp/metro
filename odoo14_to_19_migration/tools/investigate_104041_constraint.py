import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

ALL_COMPANIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

def investigate():
    ctx = {'allowed_company_ids': ALL_COMPANIES, 'active_test': False}
    
    # Search for ALL accounts with code 104041 for companies 7 and 10
    for cid in [7, 10]:
        print(f"\n--- Company {cid} ---")
        
        # Try without company filter first
        accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', '=', '104041'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code', 'active', 'company_ids'], 'context': ctx})
        print(f"  Accounts with company_ids in [{cid}]: {accs}")
        
        # Also check if archived account is blocking
        # The archived accounts for company 7 is 1803 (104041C7OLD) and company 10 is 1799 (104041C10OLD)
        # But those have DIFFERENT codes now (C7OLD, C10OLD), so they shouldn't conflict
        
        # Check if there's a shared account that includes company 7 or 10
        shared = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', '=', '104041'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code', 'active', 'company_ids'], 'context': {'allowed_company_ids': ALL_COMPANIES, 'active_test': True}})
        print(f"  Active accounts with company_ids in [{cid}]: {shared}")

if __name__ == "__main__":
    investigate()
