import xmlrpc.client
import ssl

# Configuration
URL = 'https://metro.equdaierp.com'
DB = 'metrodb'
USER = 'admin'
PASS = 'Amaze@321'

def main():
    print(f"Connecting to {URL}...")
    
    # SSL Context
    context = ssl._create_unverified_context()
    
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', context=context)
    uid = common.authenticate(DB, USER, PASS, {})
    
    if not uid:
        print("Authentication Failed!")
        return

    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    
    print("Fetching Bank/Cash Journals...")
    
    # 1. Get Journals
    journal_ids = models.execute_kw(DB, uid, PASS, 'account.journal', 'search', 
        [[('type', 'in', ('bank', 'cash'))]])
    
    if not journal_ids:
        print("No Bank/Cash journals found.")
        return

    # Read Journal Fields
    journals = models.execute_kw(DB, uid, PASS, 'account.journal', 'read', 
        [journal_ids], 
        {'fields': ['name', 'company_id', 'type', 'outbound_payment_method_line_ids', 'inbound_payment_method_line_ids', 'suspense_account_id']})

    for j in journals:
        print(f"\nJournal: {j['name']} ({j['type']}) - Company: {j['company_id'][1]}")
        if j.get('suspense_account_id'):
            print(f"  Suspense Account: {j['suspense_account_id'][1]}")
        else:
            print(f"  Suspense Account: Not Set")

        # Check Outbound (Vendor Payments)
        out_ids = j.get('outbound_payment_method_line_ids', [])
        if out_ids:
             lines = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'read', [out_ids], {'fields': ['name', 'payment_account_id']})
             print("  Outbound Payment Methods:")
             for line in lines:
                 acct = line.get('payment_account_id')
                 acct_name = acct[1] if acct else "None (Immediatly Paid)"
                 print(f"    - {line['name']}: {acct_name}")
        
        # Check Inbound (Customer Payments)
        in_ids = j.get('inbound_payment_method_line_ids', [])
        if in_ids:
             lines = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'read', [in_ids], {'fields': ['name', 'payment_account_id']})
             print("  Inbound Payment Methods:")
             for line in lines:
                 acct = line.get('payment_account_id')
                 acct_name = acct[1] if acct else "None (Immediatly Paid)"
                 print(f"    - {line['name']}: {acct_name}")

if __name__ == "__main__":
    main()
