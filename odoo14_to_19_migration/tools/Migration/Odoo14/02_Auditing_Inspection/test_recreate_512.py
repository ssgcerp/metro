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
try: models.execute_kw(db, uid, password, 'account.move', 'write', [[inv_id], {'payment_state': 'not_paid'}])
except: pass
try: models.execute_kw(db, uid, password, 'account.payment', 'write', [[pay_id], {'state': 'in_process', 'is_reconciled': False}])
except: pass

payment_data = models.execute_kw(db, uid, password, 'account.payment', 'read', [[pay_id]], {'fields': ['name', 'amount', 'date', 'partner_id', 'journal_id', 'memo']})
if not payment_data: exit()
p = payment_data[0]

# Delete broken payment 512
try: models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[pay_id]])
except: pass
try: models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [[pay_id]])
except: pass
models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[pay_id]])

# Link payment to invoice via wizard
wiz_vals = {
    'journal_id': p['journal_id'][0],
    'payment_date': p['date'],
    'amount': p['amount'],
    'communication': p['memo'],
    'payment_type': 'inbound',
    'partner_type': 'customer',
    'partner_id': p['partner_id'][0] if p.get('partner_id') else False
}

ctx = {'active_model': 'account.move', 'active_ids': [inv_id], 'active_id': inv_id}
wiz_id = models.execute_kw(db, uid, password, 'account.payment.register', 'create', [wiz_vals], {'context': ctx})
res = models.execute_kw(db, uid, password, 'account.payment.register', 'action_create_payments', [[wiz_id]], {'context': ctx})

print(f"Re-created payment for Invoice {inv_id}. Wizard response: {res}")

inv_after = models.execute_kw(db, uid, password, 'account.move', 'read', [[inv_id]], {'fields': ['payment_state']})
print(f"Invoice state is now: {inv_after[0]['payment_state']}")
