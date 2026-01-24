
import xmlrpc.client
import sys

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    print("ANALYZING 'IN PAYMENT' VENDOR BILLS")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASS, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Analyze 10 Bills in 'in_payment' with 0 residual
    domain = [('move_type', '=', 'in_invoice'), ('payment_state', '=', 'in_payment'), ('amount_residual', '=', 0)]
    ids = models.execute_kw(DB, uid, PASS, 'account.move', 'search', [domain], {'limit': 10})
    print(f"Found {len(ids)} Bills in 'in_payment' with 0 residual (Limit 10).")
    
    for bid in ids:
        bill = models.execute_kw(DB, uid, PASS, 'account.move', 'read', [[bid], ['name', 'payment_state', 'invoice_payments_widget', 'amount_residual']])[0]
        print(f"\nInspecting Bill {bill['name']} (ID {bid})...")
        print(f"  Residual: {bill['amount_residual']}")
        
        # Trace via account.partial.reconcile
        # Search lines of the bill
        b_lines = models.execute_kw(DB, uid, PASS, 'account.move.line', 'search', [[('move_id', '=', bid)]])
        
        # Search partials linked to these lines
        partials = models.execute_kw(DB, uid, PASS, 'account.partial.reconcile', 'search_read', 
            [['|', ('debit_move_id', 'in', b_lines), ('credit_move_id', 'in', b_lines)]], 
            {'fields': ['debit_move_id', 'credit_move_id', 'amount']})
            
        print(f"  Partials Found: {len(partials)}")
        for p in partials:
            did = p['debit_move_id'][0]
            cid = p['credit_move_id'][0]
            contra_id = did if did not in b_lines else cid
            
            # Read contra line
            c_line = models.execute_kw(DB, uid, PASS, 'account.move.line', 'read', [[contra_id], ['move_id', 'account_id', 'name']])[0]
            move_data = models.execute_kw(DB, uid, PASS, 'account.move', 'read', [[c_line['move_id'][0]], ['name', 'state']])[0]
            
            print(f"    -> Reconciled with Line {contra_id} in Move {move_data['name']} (Acc: {c_line['account_id'][1]})")
            print(f"       Move State: {move_data['state']}")
            
            # Find Payment linked to this move
            p_ids = models.execute_kw(DB, uid, PASS, 'account.payment', 'search', [[('move_id', '=', c_line['move_id'][0])]])
            if p_ids:
                p_rec = models.execute_kw(DB, uid, PASS, 'account.payment', 'read', [[p_ids[0]], ['name', 'state', 'outstanding_account_id']])[0]
                print(f"       -> Payment {p_rec['name']} State: {p_rec['state']} | Outstanding Acc: {p_rec['outstanding_account_id']}")

if __name__ == "__main__":
    main()
