import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

# Find payments that HAVE a move_id
pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [
    [('move_id', '!=', False)]
], {'fields': ['id', 'name', 'state', 'move_id'], 'limit': 5})

print("Payments WITH a move_id:")
for p in pays:
    print(p)
    
# Find payments without a move_id
pays_no_move = models.execute_kw(db, uid, password, 'account.payment', 'search_count', [
    [('move_id', '=', False)]
])

print(f"\nTotal Payments WITHOUT a move_id: {pays_no_move}")
