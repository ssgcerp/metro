import xmlrpc.client
import ssl
import time

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

c_id = models.execute_kw(db, uid, password, 'res.company', 'search', [[('name', '=', 'ABU DHABI')]])[0]

# Find an in_process payment that has NO move_id
pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('company_id', '=', c_id), ('state', '=', 'in_process'), ('move_id', '=', False)]
], {'fields': ['id', 'name', 'memo'], 'limit': 1})

if pays:
    p = pays[0]
    pid = p['id']
    memo = p['memo']
    print(f"Testing with Payment {p['name']} (ID {pid}), Memo: {memo}")
    
    # 2. validate the payment (action_post)
    try:
        models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[pid]])
        print("action_post succeeded.")
    except Exception as e:
        print(f"action_post failed: {e}")
        
    # Re-read payment to get move_id
    p2 = models.execute_kw(db, uid, password, 'account.payment', 'read', [[pid]], {'fields': ['move_id', 'state']})
    pay_move_id = p2[0]['move_id'][0] if p2[0].get('move_id') else False
    print(f"Payment state: {p2[0]['state']}, Move ID generated: {pay_move_id}")
    
    if pay_move_id:
        # Get payment line
        pay_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
            [('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
        ], {'fields': ['id']})
        
        if pay_lines:
            payment_line_id = pay_lines[0]['id']
            
            # Find invoice
            invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
                [('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial'])]
            ], {'fields': ['id', 'payment_state']})
            
            if invs:
                inv_id = invs[0]['id']
                print(f"Found Invoice {inv_id}. Linking lines...")
                
                # 1. link with invoice
                try:
                    res = models.execute_kw(db, uid, password, 'account.move', 'js_assign_outstanding_line', [[inv_id], payment_line_id])
                    print("Linking result:", res)
                except Exception as e:
                    print(f"Linking failed: {e}")
                    
                # 3. check the invoice payment status
                inv_after = models.execute_kw(db, uid, password, 'account.move', 'read', [[inv_id]], {'fields': ['payment_state']})
                print(f"Invoice payment status organically became: {inv_after[0]['payment_state']}")
            else:
                print("Invoice not found or already paid.")
