import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

c_id = models.execute_kw(db, uid, password, 'res.company', 'search', [[('name', '=', 'ABU DHABI')]])[0]

invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
    [('name', '=', '14596'), ('move_type', '=', 'out_invoice')]
], {'fields': ['id', 'name', 'payment_state']})

if invs:
    print(f"Invoice before: {invs[0]}")
    try:
        models.execute_kw(db, uid, password, 'account.move', 'write', [[invs[0]['id']], {'payment_state': 'paid'}])
        print("Write successful!")
    except Exception as e:
        print(f"Write failed: {e}")
        
    invs_after = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        [('id', '=', invs[0]['id'])]
    ], {'fields': ['id', 'name', 'payment_state']})
    print(f"Invoice after: {invs_after[0]}")

