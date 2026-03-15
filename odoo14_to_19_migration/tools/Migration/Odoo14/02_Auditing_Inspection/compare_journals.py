import xmlrpc.client
import ssl

url = 'https://metro.equdaierp.com'
db = 'newdb'
username = 'admin'
password = 'Amaze@321'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=ssl._create_unverified_context())
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=ssl._create_unverified_context())

j6 = models.execute_kw(db, uid, password, 'account.journal', 'read', [[6]])
j84 = models.execute_kw(db, uid, password, 'account.journal', 'read', [[84]])

diff = []
if j6 and j84:
    keys = set(j6[0].keys()).union(set(j84[0].keys()))
    for k in keys:
        v6 = j6[0].get(k)
        v84 = j84[0].get(k)
        if v6 != v84 and k not in ['id', 'name', 'code', 'sequence', 'display_name', '__last_update', 'create_date', 'write_date']:
            diff.append((k, v6, v84))

for d in diff:
    print(f"{d[0]}:\n  J6:  {d[1]}\n  J84: {d[2]}")
