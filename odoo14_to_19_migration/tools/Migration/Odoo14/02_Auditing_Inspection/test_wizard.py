import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('name', '=', 'BNK7/2025/12/0010')]
], {'fields': ['id', 'amount', 'date', 'partner_id', 'journal_id', 'memo']})

if pays:
    p = pays[0]
    print(f"Original Payment: {p}")
    
    # Unlink
    try: models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[p['id']]])
    except: pass
    try: models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [[p['id']]])
    except: pass
    try: models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[p['id']]])
    except: pass

    # Find invoice
    invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        [('name', '=', p['memo']), ('move_type', '=', 'out_invoice')]
    ], {'fields': ['id', 'name', 'payment_state']})
    
    if invs:
        inv = invs[0]
        print(f"Found Invoice: {inv}")
        
        # Create wizard
        wiz_vals = {
            'journal_id': p['journal_id'][0],
            'payment_date': p['date'],
            'amount': p['amount'],
            'communication': p['memo'],
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': p['partner_id'][0] if p.get('partner_id') else False
        }
        
        try:
            # We must pass the active_ids in context to link the wizard to the invoice
            ctx = {'active_model': 'account.move', 'active_ids': [inv['id']], 'active_id': inv['id']}
            wiz_id = models.execute_kw(db, uid, password, 'account.payment.register', 'create', [wiz_vals], {'context': ctx})
            print(f"Wizard created: {wiz_id}")
            
            # Create payment from wizard
            res = models.execute_kw(db, uid, password, 'account.payment.register', 'action_create_payments', [[wiz_id]], {'context': ctx})
            print(f"Result: {res}")
            
            # Check invoice status again
            inv_after = models.execute_kw(db, uid, password, 'account.move', 'read', [[inv['id']]], {'fields': ['payment_state']})
            print(f"Invoice state after: {inv_after[0]['payment_state']}")
        except Exception as e:
            print(f"Error wizard: {e}")

