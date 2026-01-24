
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("FIXING PAYMENTS INDIVIDUALLY (Split Companies)")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    ids = [9419, 9811]
    
    for pid in ids:
        print(f"\nProcessing Payment {pid}...")
        # Get Company
        p = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[pid], ['company_id', 'outstanding_account_id', 'name']])[0]
        cid = p['company_id'][0]
        cname = p['company_id'][1]
        print(f"  -> Company: {cname} (ID {cid})")
        
        # Find Journal for THIS Company
        j_ids = models.execute_kw(DB, uid, PASS, 'account.journal', 'search', [[('type', '=', 'bank'), ('company_id', '=', cid)]], {'limit': 1})
        if not j_ids:
             j_ids = models.execute_kw(DB, uid, PASS, 'account.journal', 'search', [[('type', '=', 'cash'), ('company_id', '=', cid)]], {'limit': 1})
             
        if not j_ids:
            print(f"  -> CRITICAL: No Journal found for Company {cid}. Skipping.")
            continue

        j = models.execute_kw(DB, uid, PASS, 'account.journal', 'read', [j_ids, ['default_account_id', 'name']])[0]
        target_acc_id = j.get('default_account_id')[0] if j.get('default_account_id') else False
        
        if not target_acc_id:
            print("  -> Journal has no default account!")
            continue
            
        print(f"  -> Found Account {target_acc_id} via Journal '{j['name']}'")
        
        # Update
        # Context to bypass checks just in case, but using correct company account should work natively
        ctx = {'check_move_validity': False, 'check_company': False} 
        try:
            models.execute_kw(DB, uid, PASS, 'account.payment', 'write', [[pid], {'outstanding_account_id': target_acc_id}], {'context': ctx})
            print("  -> Write Success.")
        except Exception as e:
            print(f"  -> Write Failed: {e}")
            continue
            
        # Validate
        try:
            models.execute_kw(DB, uid, PASS, 'account.payment', 'action_post', [[pid]], {'context': ctx})
            print("  -> Validate Success.")
        except Exception as e:
            print(f"  -> Validate Action Triggered (result: {e})")

    # Verify
    print("\nFinal Verification:")
    res = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [ids, ['state', 'outstanding_account_id']])
    for r in res:
        print(r)

if __name__ == "__main__":
    main()
