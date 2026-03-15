import xmlrpc.client
url = "https://metro.equdaierp.com"
db = "metrodb"
password = "Amaze@321"
uid = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(db,'admin',password,{})
models = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
ctx = {'allowed_company_ids': list(range(1,11)), 'active_test': False}

# Search by name Cash, type Bank and Cash
accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
    [[('name', '=', 'Cash'), ('account_type', '=', 'asset_cash')]],
    {'fields': ['id','name','code','active','company_ids'], 'context': ctx})
print(f"Found {len(accs)} 'Cash' (Bank and Cash) accounts:")
for a in sorted(accs, key=lambda x: x['id']):
    cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id','=',a['id'])]], {'context': ctx})
    marker = " <-- MASTER" if a['id'] == 232 else ""
    print(f"  ID {a['id']:5} | {a['code']:15} | Active: {a['active']} | Companies: {a['company_ids']} | Lines: {cnt}{marker}")
