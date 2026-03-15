import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

# Test writing payment state
try:
    res = models.execute_kw(db, uid, password, 'account.payment', 'write', [[512], {'state': 'paid', 'is_reconciled': True}])
    print("Payment state write:", res)
except Exception as e:
    print("Payment write error:", e)

# Test writing invoice payment_state
try:
    res = models.execute_kw(db, uid, password, 'account.move', 'write', [[4059], {'payment_state': 'paid'}])
    print("Invoice payment_state write:", res)
except Exception as e:
    print("Invoice write error:", e)
    
inv = models.execute_kw(db, uid, password, 'account.move', 'read', [[4059]], {'fields': ['payment_state']})
print("Invoice 4059 state now:", inv)
