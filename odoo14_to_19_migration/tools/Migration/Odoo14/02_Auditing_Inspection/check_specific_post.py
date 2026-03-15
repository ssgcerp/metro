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
], {'fields': ['id', 'state', 'move_id']})

try:
    models.execute_kw(db, uid, password, 'account.payment', 'action_post', [[pays[0]['id']]])
except xmlrpc.client.Fault as e:
    print(f"Odoo Fault: {e}")
except Exception as e:
    print(f"Other Error: {e}")

p2 = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('name', '=', 'BNK7/2025/12/0010')]
], {'fields': ['id', 'state', 'move_id']})

print("After Post Attempt:", p2)
