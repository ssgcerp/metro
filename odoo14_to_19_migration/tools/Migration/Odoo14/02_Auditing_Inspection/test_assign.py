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

# Find an unlinked payment
pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('company_id', '=', c_id), ('state', '=', 'in_process'), ('is_reconciled', '=', False), ('memo', '!=', False)]
], {'fields': ['id', 'name', 'memo', 'move_id'], 'limit': 1})

if pays:
    p = pays[0]
    memo = p['memo']
    print(f"Testing with Payment {p['name']} and memo {memo}")
    
    pay_move_id = p['move_id'][0] if p.get('move_id') else False
    if pay_move_id:
        pay_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
            [('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
        ], {'fields': ['id']})
        
        if pay_lines:
            payment_line_id = pay_lines[0]['id']
            
            # Find the Invoice
            invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
                [('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial']), ('company_id', '=', c_id)]
            ], {'fields': ['id', 'payment_state']})
            
            if invs:
                inv_id = invs[0]['id']
                print(f"Found Invoice {memo} ID {inv_id}, state {invs[0]['payment_state']}. Linking payment line {payment_line_id}...")
                
                try:
                    res = models.execute_kw(db, uid, password, 'account.move', 'js_assign_outstanding_line', [[inv_id], payment_line_id])
                    print("Result:", res)
                except Exception as e:
                    print("Error:", e)
                
                inv_after = models.execute_kw(db, uid, password, 'account.move', 'read', [[inv_id]], {'fields': ['payment_state']})
                print(f"Invoice state after: {inv_after[0]['payment_state']}")
                
                pay_after = models.execute_kw(db, uid, password, 'account.payment', 'read', [[p['id']]], {'fields': ['is_reconciled', 'state']})
                print(f"Payment state after: {pay_after[0]}")
