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

vals = {
    'payment_type': 'inbound',
    'partner_type': 'customer',
    'partner_id': 13330,
    'amount': 100,
    'date': '2025-12-31',
    'name': 'TEST_JOURNAL_84',
    'journal_id': 84,
    'company_id': comp[0]
}

new_id = models.execute_kw(db, uid, password, 'account.payment', 'create', [vals])
try:
    models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[new_id]])
except: pass

p2 = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('id', '=', new_id)]
], {'fields': ['id', 'state', 'move_id']})
print(f"Test Journal 84: {p2}")

# delete test payment
try:
    models.execute_kw(db, uid, password, 'account.payment', 'action_draft', [[new_id]])
    models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[new_id]])
except:
    pass
