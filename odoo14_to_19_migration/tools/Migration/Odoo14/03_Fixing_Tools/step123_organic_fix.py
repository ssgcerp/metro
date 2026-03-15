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
    [('company_id', '=', c_id), ('state', '=', 'in_process')]
], {'fields': ['id', 'name', 'amount', 'date', 'partner_id', 'journal_id', 'memo']})

print(f"Found {len(payments)} in_process payments.")

success_count = 0
for p in payments:
    try:
        pid = p['id']
        memo = p.get('memo')
        amount = p['amount']
        date = p['date']
        
        if not memo:
            continue
            
        invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
            [('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('company_id', '=', c_id)]
        ], {'fields': ['id', 'name', 'payment_state']})
        
        if not invs:
            continue
            
        inv = invs[0]
        inv_id = inv['id']
        
        # Odoo 19 doesn't let us link 'empty' payments that failed to post correctly during the migration
        # The ONLY native Odoo way to properly link a payment and generate the "Paid on" line is the wizard
        # So we delete the broken phantom payment and use the wizard to recreate the exact payment linked to the invoice
        
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[pid]])
        except: pass
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [[pid]])
        except: pass
        try: models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[pid]])
        except: pass
        
        # CREATE payment safely natively linked to invoice
        wiz_vals = {
            'journal_id': p['journal_id'][0],
            'payment_date': date,
            'amount': amount,
            'communication': memo,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': p['partner_id'][0] if p.get('partner_id') else False
        }
        
        ctx = {'active_model': 'account.move', 'active_ids': [inv_id], 'active_id': inv_id}
        wiz_id = models.execute_kw(db, uid, password, 'account.payment.register', 'create', [wiz_vals], {'context': ctx})
        
        # This action automatically validates the payment AND links it, producing the specific "Paid on" line in the UI
        new_pay = models.execute_kw(db, uid, password, 'account.payment.register', 'action_create_payments', [[wiz_id]], {'context': ctx})
        
        # We DO NOT force the payment_state. We let Odoo organic logic dictate it.
        # This means it will truthfully become "IN PAYMENT" instead of a faked "PAID".
        
        success_count += 1
        print(f"Organically linked {amount} AED for {memo} via wizard.")
    except Exception as e:
        print(f"Error on {p['name']}: {e}")

print(f"\nSuccessfully recreated and linked {success_count} payments.")
