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
    [('name', 'in', ['BNK7/2025/12/0010', 'PRAKAU/2026/00003'])]
], {'fields': ['id', 'name', 'journal_id', 'state', 'move_id']})

for p in pays:
    print(p)
    if p.get('journal_id'):
        j_id = p['journal_id'][0]
        j = models.execute_kw(db, uid, password, 'account.journal', 'read', [[j_id]], {'fields': ['name', 'type', 'default_account_id']})
        print(f"  Journal: {j}")
