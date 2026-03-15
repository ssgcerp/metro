import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def verify_names():
    print(f"--- Verifying VAT Names & Codes in {db} ---")
    
    companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})
    
    for c in companies:
        cid = c['id']
        cname = c['name']
        ctx = {'allowed_company_ids': [1, cid]}
        
        # Check Input
        vat_in = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', 'like', '104041'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
            
        # Check Output
        vat_out = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', 'like', '201017'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
            
        print(f"[{cid}] {cname}")
        for acc in vat_in:
            print(f"  IN : [{acc['code']}] {acc['name']}")
        for acc in vat_out:
            print(f"  OUT: [{acc['code']}] {acc['name']}")

if __name__ == "__main__":
    verify_names()
