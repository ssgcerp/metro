import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

pays = models.execute_kw(db, uid, password, 'account.payment.method.line', 'search_read', [
    [('id', 'in', [87, 88, 69, 70, 120])]
], {'fields': ['name', 'payment_account_id', 'journal_id']})

for p in pays:
    print(p)
