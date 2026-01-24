
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("Connecting...")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # 1. Find a Journal with Outstanding Account set
    # We look for one used in migration?
    # Or just search any Bank/Cash
    j_ids = models.execute_kw(DB, uid, PASS, 'account.journal', 'search', [[('type', 'in', ['bank', 'cash'])]], {'limit': 1})
    if not j_ids:
        print("No Bank/Cash journal found.")
        return
    
    jid = j_ids[0]
    j_data = models.execute_kw(DB, uid, PASS, 'account.journal', 'read', [jid, ['name', 'payment_credit_account_id', 'default_account_id']])
    print(f"Journal: {j_data}")
    
    # 2. Check if we can clear Outstanding Account
    # We must ensure default_account_id is set
    if not j_data[0]['default_account_id']:
        print("Journal has no Default Bank Account! Can't test Direct Posting.")
        return

    print("Attempting to Clear Outstanding Account and Create Test Payment...")
    # NOTE: We won't actually clear it permanently, just testing logic? 
    # But to test posting, we must clear it.
    # We will restore it after? 
    # Or better: Create a duplicate Test Journal.
    
    # Create Test Journal
    test_j_vals = {
        'name': 'TEST Direct Post Journal',
        'code': 'TSTDP',
        'type': 'bank',
        'default_account_id': j_data[0]['default_account_id'][0],
        # Explicitly NO outstanding
        'payment_credit_account_id': False,
        'payment_debit_account_id': False,
    }
    
    # We might need to copy logic from 'bank'
    try:
        new_j_id = models.execute_kw(DB, uid, PASS, 'account.journal', 'create', [test_j_vals])
        print(f"Created Test Journal ID: {new_j_id}")
        
        # Create Payment
        pay_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': 10.0,
            'journal_id': new_j_id,
            'payment_method_line_id': False # Let default pick? Or need one?
        }
        # Need payment method line?
        # Get one
        pm_lines = models.execute_kw(DB, uid, PASS, 'account.payment.method.line', 'search', [[('journal_id', '=', new_j_id), ('name', 'ilike', 'Manual')]], {'limit': 1})
        if pm_lines:
            pay_vals['payment_method_line_id'] = pm_lines[0]
            
        pid = models.execute_kw(DB, uid, PASS, 'account.payment', 'create', [pay_vals])
        print(f"Created Payment ID: {pid}")
        
        # Post
        models.execute_kw(DB, uid, PASS, 'account.payment', 'action_post', [[pid]])
        
        # Check State
        p_res = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[pid], ['state', 'is_reconciled', 'move_id']])
        print(f"Payment State: {p_res[0]['state']}")
        
        # Check Move Lines (to see if it hit Bank directly)
        mid = p_res[0]['move_id'][0]
        lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'read', [models.execute_kw(DB, uid, PASS, 'account.move.line', 'search', [[('move_id', '=', mid)]])], {'fields': ['account_id', 'name']})
        for l in lines:
            print(f" - Line: {l['account_id'][1]} | {l['name']}")

    except Exception as e:
        print(f"Test Failed: {e}")
    finally:
        # Cleanup (Optional, but good practice)
        pass

if __name__ == "__main__":
    main()
