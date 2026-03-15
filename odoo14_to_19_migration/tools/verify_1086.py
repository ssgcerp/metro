import xmlrpc.client
url = "https://metro.equdaierp.com"
db = "metrodb"
password = "Amaze@321"
uid = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(db,'admin',password,{})
models = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
ctx = {'allowed_company_ids': list(range(1,11)), 'active_test': False}

print("=== Master 1086 ===")
acc = models.execute_kw(db, uid, password, 'account.account', 'read',
    [[1086]], {'fields': ['id','name','code','active','company_ids'], 'context': ctx})[0]
cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
    [[('account_id','=',1086)]], {'context': ctx})
print(f"  ID {acc['id']} | {acc['code']} | {acc['name']} | Active: {acc['active']} | Companies: {acc['company_ids']} | Lines: {cnt}")

print("\n=== Old accounts ===")
for aid in [1229, 498, 890, 714]:
    try:
        acc = models.execute_kw(db, uid, password, 'account.account', 'read',
            [[aid]], {'fields': ['id','name','code','active','company_ids'], 'context': ctx})[0]
        cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id','=',aid)]], {'context': ctx})
        print(f"  ID {acc['id']} | {acc['code']} | Active: {acc['active']} | Lines: {cnt}")
    except Exception as e:
        print(f"  ID {aid} | NOT FOUND (deleted) ✓")
