import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

try:
    models.execute_kw(db, uid, password, 'account.move.line', 'reconcile', [[703, 63425]])
    print("Reconciled successfully")
except Exception as e:
    print(f"Error: {e}")
