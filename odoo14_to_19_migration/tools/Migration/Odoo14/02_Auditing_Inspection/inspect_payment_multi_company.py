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
    
    print("Listing Allowed Companies...")
    user = models.execute_kw(DB, uid, PASS, 'res.users', 'read', [uid], {'fields': ['company_ids']})
    allowed_company_ids = user[0]['company_ids']
    
    print(f"User has access to {len(allowed_company_ids)} companies.")
    
    for cid in allowed_company_ids:
        # Context inside kwargs
        ctx = {'allowed_company_ids': [cid]}
        
        # Search for Journal in this company
        # execute_kw(db, uid, password, model, method, args, kwargs)
        # search_read(domain, fields=None, offset=0, limit=None, order=None)
        
        # Correct syntax for search_read via execute_kw:
        # args = [domain]
        # kwargs = {fields: [...], context: ...}
        
        journals = models.execute_kw(DB, uid, PASS, 'account.journal', 'search_read', 
            [[('name', 'ilike', 'ADCB'), ('company_id', '=', cid)]], 
            {'fields': ['name', 'company_id', 'outbound_payment_method_line_ids'], 'context': ctx})
            
        if journals:
            print(f"\n--- Company ID {cid} ---")
            for j in journals:
                print(f"Found Journal: {j['name']} (ID: {j['id']}) in {j['company_id'][1]}")
                
                # Check config
                out_ids = j['outbound_payment_method_line_ids']
                if out_ids:
                    # We need to read lines. Read method takes IDs list as args[0].
                    lines = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'read', [out_ids], {'fields': ['name', 'payment_account_id']})
                    for line in lines:
                        acct = line.get('payment_account_id')
                        status = "Immediate (No Account)" if not acct else f"Outstanding: {acct[1]}"
                        print(f"    Method '{line['name']}': {status}")
                        
        # Search for payment
        # Name: PADCB3/2026/00016 OR Amount: 525.0
        domain = ['|', ('name', '=', 'PADCB3/2026/00016'), ('amount', '=', 525.0)]
        payments = models.execute_kw(DB, uid, PASS, 'account.payment', 'search_read', 
            [domain], 
            {'fields': ['name', 'amount', 'state', 'company_id', 'journal_id'], 'limit': 5, 'context': ctx})
            
        if payments:
             for p in payments:
                 print(f"  -> Found Payment: {p['name']} (ID: {p['id']}) in {p['company_id'][1]}")
                 print(f"     Amount: {p['amount']}")
                 print(f"     State: {p['state']}")
                 print(f"     Journal: {p['journal_id'][1]}")

if __name__ == "__main__":
    main()
