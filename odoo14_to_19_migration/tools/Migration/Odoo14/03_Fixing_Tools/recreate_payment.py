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

pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('name', '=', 'BNK7/2025/12/0010')]
], {'fields': ['id', 'amount', 'date', 'partner_id', 'journal_id', 'memo']})

if pays:
    p = pays[0]
    print(f"Original: {p}")
    vals = {
        'payment_type': 'inbound',
        'partner_type': 'customer',
        'partner_id': p['partner_id'][0] if p.get('partner_id') else False,
        'amount': p['amount'],
        'date': p['date'],
        'name': 'BNK7/2025/12/0010',
        'journal_id': p['journal_id'][0],
        'company_id': comp[0],
        'memo': p.get('memo', '')
    }
    # Unlink original
    try:
        models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[p['id']]])
    except: pass
    try:
        models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [[p['id']]])
    except: pass
    models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[p['id']]])
    
    # Create new
    new_id = models.execute_kw(db, uid, password, 'account.payment', 'create', [vals])
    try:
        models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[new_id]])
    except: pass
    
    p2 = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
        [('id', '=', new_id)]
    ], {'fields': ['id', 'state', 'move_id']})
    print(f"Re-created: {p2}")
