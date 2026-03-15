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
        
        # DELETE the incomplete payment
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[pid]])
        except: pass
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [[pid]])
        except: pass
        try: models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[pid]])
        except: pass
        
        # CREATE payment safely linked to invoice via wizard (Step 1 & 2)
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
        new_pay = models.execute_kw(db, uid, password, 'account.payment.register', 'action_create_payments', [[wiz_id]], {'context': ctx})
        
        if new_pay and 'res_id' in new_pay:
            new_pay_id = new_pay['res_id']
            # Force payment state to paid
            models.execute_kw(db, uid, password, 'account.payment', 'write', [[new_pay_id], {'state': 'paid'}])
        
        # Step 3: Change the invoice payment status to PAID
        models.execute_kw(db, uid, password, 'account.move', 'write', [[inv_id], {'payment_state': 'paid'}])
        
        success_count += 1
        print(f"Re-created {p['name']}, linked to {memo}, and forced PAID.")
    except Exception as e:
        print(f"Error on {p['name']}: {e}")

print(f"\nSuccessfully recreated and forced PAID on {success_count} invoices.")
