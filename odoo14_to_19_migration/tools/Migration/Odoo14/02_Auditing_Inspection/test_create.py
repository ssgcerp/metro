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
    'partner_id': 14327,
    'amount': 100,
    'date': '2025-01-01',
    'name': 'TEST_PAYMENT_99',
    'journal_id': 84,
    'company_id': comp[0]
}
pay_id = models.execute_kw(db, uid, password, 'account.payment', 'create', [vals])
p = models.execute_kw(db, uid, password, 'account.payment', 'read', [[pay_id]], {'fields': ['name', 'state', 'move_id']})
print("Draft:", p)

try:
    res = models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[pay_id]])
    print("Action post res:", res)
except Exception as e:
    pass # we know it returns None

p2 = models.execute_kw(db, uid, password, 'account.payment', 'read', [[pay_id]], {'fields': ['name', 'state', 'move_id']})
print("Posted:", p2)

# Unlink it if draft, otherwise cancel then unlink
state = p2[0]['state']
if state != 'draft':
    models.execute_kw(db, uid, password, 'account.payment', 'action_cancel', [[pay_id]])
models.execute_kw(db, uid, password, 'account.payment', 'unlink', [[pay_id]])
print("Cleanup done.")
