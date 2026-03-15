import xmlrpc.client
import ssl
from pprint import pprint

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('name', '=', 'PBNK1/2023/00185')]
], {'limit': 1})

if pays:
    print("Payment details (ALL FIELDS):")
    for k, v in pays[0].items():
        if k in ['id', 'name', 'memo', 'state', 'partner_id', 'amount', 'is_reconciled', 'move_id', 'line_ids', 'journal_id']:
            print(f"{k}: {v}")
    
    memo = pays[0]['memo']
    invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        [('name', '=', memo)]
    ], {'fields': ['id', 'name', 'state', 'payment_state', 'move_type', 'company_id']})
    
    print(f"\nInvoices found matching memo {memo}:")
    for i in invs:
        pprint(i)
else:
    print("Payment not found.")
