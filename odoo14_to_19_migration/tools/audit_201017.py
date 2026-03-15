import xmlrpc.client
url = "https://metro.equdaierp.com"
db = "metrodb"
password = "Amaze@321"
uid = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(db,'admin',password,{})
models = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
ctx = {'allowed_company_ids': list(range(1,11)), 'active_test': False}

accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
    [[('code','like','201017')]],
    {'fields': ['id','name','code','active','company_ids'], 'context': ctx})
print(f"Remaining 201017 accounts: {len(accs)}")
for a in accs:
    cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id','=',a['id'])]], {'context': ctx})
    print(f"  ID {a['id']} | {a['name']} | Active: {a['active']} | Companies: {a['company_ids']} | Lines: {cnt}")
