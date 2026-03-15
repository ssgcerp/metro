import xmlrpc.client
import ssl
from pprint import pprint

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('name', '=', 'PBNK1/2023/00185')]
], {'limit': 1})

if pays:
    pay_id = pays[0]['id']
    print(f"Calling action_post on Payment {pay_id}...")
    try:
        res = models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[pay_id]])
        print(f"action_post result: {res}")
    except Exception as e:
        print(f"Error calling action_post: {e}")
        
    pays_after = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
        [('id', '=', pay_id)]
    ], {'fields': ['id', 'state', 'move_id']})
    print(f"Payment after: {pays_after}")
else:
    print("Payment not found.")
