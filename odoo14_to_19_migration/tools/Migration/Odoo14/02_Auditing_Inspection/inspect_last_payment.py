import xmlrpc.client
import ssl

URL = 'https://metro.equdaierp.com'
DB = 'metrodb'
USER = 'admin'
PASS = 'Amaze@321'

def main():
    context = ssl._create_unverified_context()
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', context=context)
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    
    # Get Abu Dhabi Company ID
    companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search_read', 
        [[('name', 'ilike', 'ABU DHABI')]], {'fields': ['name']})
        
    if not companies:
        print("Abu Dhabi Company NOT FOUND")
        return
        
    cid = companies[0]['id']
    print(f"Checking in {companies[0]['name']} (ID: {cid})...")
    
    # Find last payment
    payments = models.execute_kw(DB, uid, PASS, 'account.payment', 'search_read', 
        [[]], 
        {'fields': ['name', 'amount', 'state', 'journal_id', 'is_reconciled'], 'limit': 1, 'order': 'id desc', 'context': {'allowed_company_ids': [cid]}})

    if payments:
        p = payments[0]
        print(f"Last Payment: {p['name']} (ID: {p['id']})")
        print(f"  State: {p['state']}")
        print(f"  Journal: {p['journal_id'][1]}")
        print(f"  Reconciled: {p['is_reconciled']}")
    else:
        print("No payments found in Abu Dhabi.")

if __name__ == "__main__":
    main()
