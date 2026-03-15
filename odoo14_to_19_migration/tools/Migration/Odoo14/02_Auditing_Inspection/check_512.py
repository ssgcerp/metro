import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

pay_id = 512
inv_id = 4059

payment = models.execute_kw(db, uid, password, 'account.payment', 'read', [[pay_id]], {'fields': ['name', 'memo', 'state', 'partner_id', 'is_reconciled', 'move_id']})
print(f"Payment 512: {payment}")

invoice = models.execute_kw(db, uid, password, 'account.move', 'read', [[inv_id]], {'fields': ['name', 'state', 'payment_state', 'move_type', 'company_id']})
print(f"Invoice 4059: {invoice}")

# Also let's check what the search query yields
memo = payment[0].get('memo')
if memo:
    invs = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
        [('name', '=', memo), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
    ], {'fields': ['id', 'name', 'payment_state']})
    print(f"Search by memo '{memo}': {invs}")
