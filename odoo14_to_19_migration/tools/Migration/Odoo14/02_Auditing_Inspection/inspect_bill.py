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
    
    bill_ref = 'MFS/BILL/AUH/1898-2026'
    print(f"Searching for Bill '{bill_ref}'...")
    
    # Search across companies
    user = models.execute_kw(DB, uid, PASS, 'res.users', 'read', [uid], {'fields': ['company_ids']})
    allowed_company_ids = user[0]['company_ids']
    
    found = False
    for cid in allowed_company_ids:
        ctx = {'allowed_company_ids': [cid]}
        bills = models.execute_kw(DB, uid, PASS, 'account.move', 'search_read', 
            [['|', ('name', '=', bill_ref), ('ref', '=', bill_ref)]], 
            {'fields': ['name', 'payment_state', 'state', 'amount_residual', 'company_id'], 'context': ctx})
            
        if bills:
            found = True
            for b in bills:
                print(f"Found Bill: {b['name']} (ID: {b['id']}) in {b['company_id'][1]}")
                print(f"  State: {b['state']}") # Posted
                print(f"  Payment State: {b['payment_state']}") # Expected: paid
                print(f"  Amount Due: {b['amount_residual']}")

    if not found:
        print("Bill NOT FOUND.")

if __name__ == "__main__":
    main()
