import xmlrpc.client
import ssl

# Configuration
URL = 'https://metro.equdaierp.com'
DB = 'metrodb'
USER = 'admin'
PASS = 'Amaze@321'

def main():
    context = ssl._create_unverified_context()
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common', context=context)
    uid = common.authenticate(DB, USER, PASS, {})
    
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    
    # Check "Bank" journal for "Mysore Restaurant"
    # We search by name and company name (using ilike for safety)
    
    # First find company
    companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search_read', 
        [[('name', 'ilike', 'Mysore')]], {'fields': ['name']})
        
    if not companies:
        print("Mysore company not found")
        return
        
    company_id = companies[0]['id']
    company_name = companies[0]['name']
    
    print(f"Checking 'Bank' Journal for {company_name}...")
    
    journals = models.execute_kw(DB, uid, PASS, 'account.journal', 'search_read', 
        [[('name', '=', 'Bank'), ('company_id', '=', company_id)]], 
        {'fields': ['name', 'outbound_payment_method_line_ids']})
        
    if not journals:
        print("Journal not found")
        return
        
    journal = journals[0]
    
    out_ids = journal.get('outbound_payment_method_line_ids', [])
    if out_ids:
         lines = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'read', [out_ids], {'fields': ['name', 'payment_account_id']})
         
         for line in lines:
             acct = line.get('payment_account_id')
             status = "Safe (Immediate Paid)" if not acct else f"Outstanding Account: {acct[1]}"
             print(f"  - Method '{line['name']}': {status}")

if __name__ == "__main__":
    main()
