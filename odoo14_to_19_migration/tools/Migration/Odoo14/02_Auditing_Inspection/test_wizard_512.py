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
pay_id = 512
inv_id = 4059

# Force clear bad states from invoice first just in case
models.execute_kw(db, uid, password, 'account.move', 'write', [[inv_id], {'payment_state': 'not_paid'}])

# Read payment 512 to get data
payment_data = models.execute_kw(db, uid, password, 'account.payment', 'read', [[pay_id]], {'fields': ['name', 'amount', 'date', 'partner_id', 'journal_id', 'memo']})
if payment_data:
    p = payment_data[0]
    
    # Unlink bad payment 512
    try: models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[pay_id]])
    except: pass
    try: models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[pay_id]])
    except: pass

    # 1. Use the wizard to create the payment IN THE CONTEXT OF THE INVOICE
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
    print(f"Wizard {wiz_id} created.")
    
    # 2. Let wizard validate and auto-link payment
    res = models.execute_kw(db, uid, password, 'account.payment.register', 'action_create_payments', [[wiz_id]], {'context': ctx})
    print(f"Wizard result: {res}")
    
    # Read organic invoice state
    inv_after = models.execute_kw(db, uid, password, 'account.move', 'read', [[inv_id]], {'fields': ['payment_state']})
    print(f"Invoice organically became: {inv_after[0]['payment_state']}")
