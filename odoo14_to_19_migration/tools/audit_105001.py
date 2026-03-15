import xmlrpc.client
url = "https://metro.equdaierp.com"
db = "metrodb"
password = "Amaze@321"
uid = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(db,'admin',password,{})
models = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
ctx = {'allowed_company_ids': list(range(1,11)), 'active_test': False}

accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
    [[('code', 'like', '105001')]],
    {'fields': ['id','name','code','active','company_ids'], 'context': ctx})
print(f"Found {len(accs)} accounts with code like 105001:")
for a in accs:
    cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id','=',a['id'])]], {'context': ctx})
    print(f"  ID {a['id']:5} | {a['code']:15} | {a['name']:30} | Active: {a['active']} | Companies: {a['company_ids']} | Lines: {cnt}")
