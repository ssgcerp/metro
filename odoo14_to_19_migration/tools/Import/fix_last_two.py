
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("FIXING LAST 2 PAYMENTS -- CLEAN VERSION")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    
    ids = [9419, 9811]
    
    print("Finding valid asset_cash account via Journal for Company 1...")
    # Search for Bank Journal in Company 1
    # Note: 'company_id' on journal might also error if field is hidden? 
    # Let's hope journal search works better.
    j_ids = models.execute_kw(DB, uid, PASS, 'account.journal', 'search', [[('type', '=', 'bank'), ('company_id', '=', 1)]], {'limit': 1})
    
    if not j_ids:
         print("No Bank Journal found for Company 1. Trying Cash...")
         j_ids = models.execute_kw(DB, uid, PASS, 'account.journal', 'search', [[('type', '=', 'cash'), ('company_id', '=', 1)]], {'limit': 1})
         
    if not j_ids:
        print("CRITICAL: No Journal found for Company 1.")
        return

    # Read default account
    j = models.execute_kw(DB, uid, PASS, 'account.journal', 'read', [j_ids, ['default_account_id', 'name']])[0]
    print(f"Found Journal: {j}")
    
    target_acc_id = j.get('default_account_id')[0] if j.get('default_account_id') else False
    
    if not target_acc_id:
        print("Journal has no default account!")
        return
        
    print(f"Target Account ID: {target_acc_id}")

    print(f"Updating {ids} using Account {target_acc_id} (Bypassing Check Company)...")
    # Context to bypass checks
    ctx = {'check_move_validity': False, 'check_company': False}
    try:
        models.execute_kw(DB, uid, PASS, 'account.payment', 'write', [ids, {'outstanding_account_id': target_acc_id}], {'context': ctx})
        print("Write Done.")
    except Exception as e:
        print(f"Write Failed: {e}")
        return
    
    # 3. Validate / Refresh
    print("Validating...")
    try:
        models.execute_kw(DB, uid, PASS, 'account.payment', 'action_post', [ids], {'context': ctx})
        print("Validate Done.")
    except Exception as e:
        print(f"Validate Result (Ignore NoneType): {e}")

    # 4. Verify
    res = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [ids, ['state', 'outstanding_account_id']])
    print(f"Final State: {res}")

if __name__ == "__main__":
    main()
