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
    
    # 1. Get Allowed Companies
    user = models.execute_kw(DB, uid, PASS, 'res.users', 'read', [uid], {'fields': ['company_ids']})
    allowed_company_ids = user[0]['company_ids']
    
    target_journal_name = "ADCB 14344957920001 AUH"
    print(f"Searching for Journal '{target_journal_name}'...")
    
    found_journal = False
    
    for cid in allowed_company_ids:
        ctx = {'allowed_company_ids': [cid]}
        
        journals = models.execute_kw(DB, uid, PASS, 'account.journal', 'search_read', 
            [[('name', '=', target_journal_name)]], 
            {'fields': ['name', 'company_id', 'outbound_payment_method_line_ids'], 'context': ctx})
            
        for j in journals:
            found_journal = True
            print(f"\n[FOUND] Journal '{j['name']}' (ID: {j['id']}) in Company '{j['company_id'][1]}'")
            
            # Check Config
            out_ids = j['outbound_payment_method_line_ids']
            if out_ids:
                lines = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'read', [out_ids], {'fields': ['name', 'payment_account_id']})
                for line in lines:
                    acct = line.get('payment_account_id')
                    status = "Immediate (No Account)" if not acct else f"Outstanding: {acct[1]}"
                    print(f"  Method '{line['name']}': {status}")
                    
    if not found_journal:
        print("Journal NOT FOUND in any allowed company.")

if __name__ == "__main__":
    main()
