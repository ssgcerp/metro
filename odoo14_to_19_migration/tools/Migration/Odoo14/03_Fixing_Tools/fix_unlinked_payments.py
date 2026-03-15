import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

comp = models.execute_kw(db, uid, password, 'res.company', 'search', [[('name', '=', 'ABU DHABI')]])
c_id = comp[0]

print("Fetching 'in_process' payments for ABU DHABI...")
pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('company_id', '=', c_id), ('state', '=', 'in_process')]
], {'fields': ['id', 'name', 'amount', 'date', 'partner_id', 'journal_id', 'memo']})

print(f"Total found: {len(pays)}")

success_count = 0
failed_count = 0

for p in pays:
    try:
        pid = p['id']
        memo = p.get('memo')
        amount = p['amount']
        date = p['date']
        
        if not memo:
            continue
            
        # Find matching open invoice
        invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
            [('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid'), ('company_id', '=', c_id)]
        ], {'fields': ['id', 'name', 'payment_state']})
        
        if not invs:
            # Invoice not found or already paid
            continue
            
        inv = invs[0]
        
        # 1. DELETE the corrupted unlinked payment
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[pid]])
        except: pass
        try: models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [[pid]])
        except: pass
        try: models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[pid]])
        except: pass
        
        # 2. CREATE payment safely linked to invoice via wizard
        wiz_vals = {
            'journal_id': p['journal_id'][0],
            'payment_date': date,
            'amount': amount,
            'communication': memo,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': p['partner_id'][0] if p.get('partner_id') else False
        }
        
        ctx = {'active_model': 'account.move', 'active_ids': [inv['id']], 'active_id': inv['id']}
        wiz_id = models.execute_kw(db, uid, password, 'account.payment.register', 'create', [wiz_vals], {'context': ctx})
        
        models.execute_kw(db, uid, password, 'account.payment.register', 'action_create_payments', [[wiz_id]], {'context': ctx})
        
        print(f"Successfully linked & validated {p['name']} with invoice {memo}")
        success_count += 1
    except Exception as e:
        print(f"Failed processing {p['name']}: {e}")
        failed_count += 1

print(f"Finished fixing unlinked payments. Success: {success_count}. Failed: {failed_count}.")
