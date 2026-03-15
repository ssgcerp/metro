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
    
    print("Searching for payments with Amount=525.00...")
    
    # Search by Amount
    payments = models.execute_kw(DB, uid, PASS, 'account.payment', 'search_read', 
        [[('amount', '=', 525.0), ('date', '=', '2026-02-12')]], 
        {'fields': ['name', 'amount', 'partner_id', 'journal_id', 'state', 'company_id']})
        
    if not payments:
        print("No matching payments found.")
    else:
        for p in payments:
            print(f"\nFound Payment: {p['name']} (ID: {p['id']})")
            print(f"  Company: {p['company_id'][1]}")
            print(f"  Journal: {p['journal_id'][1]}")
            print(f"  State: {p['state']}")
            
            # Inspect Journal Config for this one
            journal_id = p['journal_id'][0]
            j = models.execute_kw(DB, uid, PASS, 'account.journal', 'read', [journal_id], 
                {'fields': ['outbound_payment_method_line_ids']})
            
            out_ids = j[0]['outbound_payment_method_line_ids']
            if out_ids:
                lines = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'read', [out_ids], {'fields': ['name', 'payment_account_id']})
                for line in lines:
                    acct = line.get('payment_account_id')
                    status = "Immediate (No Account)" if not acct else f"Outstanding: {acct[1]}"
                    print(f"    Method '{line['name']}': {status}")

if __name__ == "__main__":
    main()
