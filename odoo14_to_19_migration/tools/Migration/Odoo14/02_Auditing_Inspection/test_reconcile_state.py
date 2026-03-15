import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

# Get invoice
invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
    [('name', '=', '15268'), ('move_type', '=', 'out_invoice')]
], {'fields': ['id', 'name', 'payment_state']})
print(f"Invoice state: {invs}")
