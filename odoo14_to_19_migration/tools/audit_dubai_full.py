import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def audit_dubai_full():
    print(f"--- Audit ALL Dubai (ID 3) Accounts ---")
    
    cid = 3
    ctx = {'allowed_company_ids': [1, cid], 'active_test': False}
    
    accounts = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('company_ids', 'in', [cid])]],
        {'fields': ['id', 'name', 'code', 'active'], 'context': ctx})
        
    print(f"Found {len(accounts)} accounts:")
    for a in accounts:
        # Check against likely culprits
        if '201017' in str(a['code']) or 'VAT' in a['name'] or 'TMP' in str(a['code']):
            print(f"  MATCH: ID: {a['id']} | Code: {a['code']} | Name: {a['name']} | Active: {a['active']}")

if __name__ == "__main__":
    audit_dubai_full()
