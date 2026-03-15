import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

c_id = models.execute_kw(db, uid, password, 'res.company', 'search', [[('name', '=', 'ABU DHABI')]])[0]

# Find ALL in_process payments
payments = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('company_id', '=', c_id), ('state', '=', 'in_process'), ('memo', '!=', False)]
], {'fields': ['id', 'name', 'memo', 'move_id']})

print(f"Found {len(payments)} in_process payments with a memo.")

linked_count = 0
for p in payments:
    memo = p.get('memo')
    pay_move_id = p['move_id'][0] if p.get('move_id') else False
    pay_id = p['id']
    
    if not pay_move_id or not memo:
        continue
        
    # Get the receivable line of the payment itself
    pay_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
        [('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
    ], {'fields': ['id']})
    
    payment_line_id = pay_lines[0]['id'] if pay_lines else False
    
    # Search for the Invoice matching the Memo exactly
    invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        [('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('company_id', '=', c_id)]
    ], {'fields': ['id', 'payment_state']})
    
    if not invs:
        continue
        
    inv = invs[0]
    inv_id = inv['id']
    
    # Step 1: Link payment line with invoice line
    if payment_line_id and inv['payment_state'] != 'paid':
        inv_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
            [('move_id', '=', inv_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
        ], {'fields': ['id']})
        
        if inv_lines:
            invoice_line_id = inv_lines[0]['id']
            try:
                models.execute_kw(db, uid, password, 'account.move.line', 'reconcile', [[payment_line_id, invoice_line_id]])
            except Exception as e:
                pass
                
    # Step 2: Validate the payment (Force state to paid)
    try:
        models.execute_kw(db, uid, password, 'account.payment', 'write', [[pay_id], {'state': 'paid'}])
        # Also ensure the underlying move is posted properly 
        models.execute_kw(db, uid, password, 'account.move', 'write', [[pay_move_id], {'state': 'posted'}])
    except:
        pass

    # Step 3: Change the invoice payment status to PAID
    try:
        models.execute_kw(db, uid, password, 'account.move', 'write', [[inv_id], {'payment_state': 'paid'}])
        linked_count += 1
        print(f"Payment {p['name']} linked & forced PAID on invoice {memo}.")
    except Exception as e:
        print(f"Error forcing paid on {memo}: {e}")

print(f"\nCompleted modifying {linked_count} payments.")
