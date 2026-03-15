import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context(), allow_none=True)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context(), allow_none=True)

pays = models.execute_kw(db, uid, password, 'account.payment', 'search_read', [[('state', '=', 'in_process')]], {'fields': ['name', 'company_id']})
print(f'Found {len(pays)} payments.')

for p in pays:
    cid = p['company_id'][0]
    ctx = {'allowed_company_ids': [1, cid]}
    try:
        models.execute_kw(db, uid, password, 'account.payment', 'write', [[p['id']], {'state': 'paid'}], {'context': ctx})
        print(f"Forced {p['name']} in company {cid}")
    except Exception as e:
        print(f"Error on {p['name']}: {e}")
print("Done.")
