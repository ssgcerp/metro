import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

pay_id = 512
inv_id = 4059

# First revert the forced states from my previous script
try:
    # Set invoice back to partial/not_paid
    models.execute_kw(db, uid, password, 'account.move', 'write', [[inv_id], {'payment_state': 'not_paid'}])
    
    # Revert payment 512 back to in_process
    models.execute_kw(db, uid, password, 'account.payment', 'write', [[pay_id], {'state': 'in_process', 'is_reconciled': False}])
except Exception as e:
    print(f"Error reverting states: {e}")

# Find payment line
payment = models.execute_kw(db, uid, password, 'account.payment', 'read', [[pay_id]], {'fields': ['move_id']})
pay_move_id = payment[0]['move_id'][0]

pay_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read', [
    [('move_id', '=', pay_move_id), ('account_id.account_type', '=', 'asset_receivable'), ('reconciled', '=', False)]
], {'fields': ['id']})

if pay_lines:
    payment_line_id = pay_lines[0]['id']
    print(f"Linking payment line {payment_line_id} to invoice {inv_id}...")
    try:
        res = models.execute_kw(db, uid, password, 'account.move', 'js_assign_outstanding_line', [[inv_id], payment_line_id])
        print("Result:", res)
    except Exception as e:
        print("Error:", e)
        
    inv = models.execute_kw(db, uid, password, 'account.move', 'read', [[inv_id]], {'fields': ['payment_state']})
    print("Invoice state after native link:", inv[0]['payment_state'])
else:
    print("Could not find open receivable line on payment.")
