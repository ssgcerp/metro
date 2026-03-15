import xmlrpc.client
import ssl

# Configuration
URL = 'https://metro.equdaierp.com'
DB = 'metrodb'
USER = 'admin'
PASS = 'Amaze@321'

def main():
    print(f"Connecting to {URL}...")
    context = ssl._create_unverified_context()
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', context=context)
    uid = common.authenticate(DB, USER, PASS, {})
    
    if not uid:
        print("Authentication Failed!")
        return

    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    
    print("Scanning Journals for Outstanding Accounts...")
    
    # Get Bank/Cash Journals
    journal_ids = models.execute_kw(DB, uid, PASS, 'account.journal', 'search', 
        [[('type', 'in', ('bank', 'cash'))]])
    
    if not journal_ids:
        print("No journals found.")
        return

    journals = models.execute_kw(DB, uid, PASS, 'account.journal', 'read', 
        [journal_ids], 
        {'fields': ['name', 'company_id', 'outbound_payment_method_line_ids', 'inbound_payment_method_line_ids']})

    params_to_update = [] # List of (id, vals) for account.payment.method.line

    for j in journals:
        print(f"\nProcessing {j['name']} ({j['company_id'][1]})...")
        
        # Check Outbound (Vendor Bills)
        out_ids = j.get('outbound_payment_method_line_ids', [])
        if out_ids:
             lines = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'read', [out_ids], {'fields': ['name', 'payment_account_id']})
             
             for line in lines:
                 if line.get('payment_account_id'):
                     print(f"  [FIX] Removing Outbound Account '{line['payment_account_id'][1]}' from method '{line['name']}'")
                     params_to_update.append(line['id'])
        
        # Check Inbound (Customer Invoices) - Optional, but keeping consistent
        in_ids = j.get('inbound_payment_method_line_ids', [])
        if in_ids:
             lines = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'read', [in_ids], {'fields': ['name', 'payment_account_id']})
             
             for line in lines:
                 if line.get('payment_account_id'):
                     print(f"  [FIX] Removing Inbound Account '{line['payment_account_id'][1]}' from method '{line['name']}'")
                     params_to_update.append(line['id'])

    if not params_to_update:
        print("\nNo adjustments needed. All journals are already set to immediate payment.")
        return

    print(f"\nIdentified {len(params_to_update)} payment lines to update.")
    confirm = input("Do you want to apply these changes? (yes/no): ")
    
    if confirm.lower() == 'yes':
        # Apply updates
        # We can't write multiple different values in one call easily if they were different, 
        # but here we are setting ALL found lines to payment_account_id = False
        
        count = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'write', 
            [params_to_update, {'payment_account_id': False}])
            
        print(f"Successfully updated {len(params_to_update)} lines. Payments should now be 'PAID' immediately.")
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    main()
