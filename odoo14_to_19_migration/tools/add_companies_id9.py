import xmlrpc.client
url = "https://metro.equdaierp.com"
db = "metrodb"
password = "Amaze@321"
uid = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(db,'admin',password,{})
models = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
ctx = {'allowed_company_ids': list(range(1,11)), 'active_test': False}

# Check what ID 9 is
acc = models.execute_kw(db, uid, password, 'account.account', 'read',
    [[9]], {'fields': ['id','name','code','active','company_ids'], 'context': ctx})[0]
print(f"ID 9: {acc['code']} | {acc['name']} | Companies before: {acc['company_ids']}")

# Add all companies via SQL server action
model_id = models.execute_kw(db, uid, password, 'ir.model', 'search', [[('model','=','account.account')]])[0]
sql = ("env.cr.execute('INSERT INTO account_account_res_company_rel (account_account_id, res_company_id) "
       "SELECT 9, id FROM res_company "
       "WHERE id NOT IN (SELECT res_company_id FROM account_account_res_company_rel WHERE account_account_id = 9)')")
action_id = models.execute_kw(db, uid, password, 'ir.actions.server', 'create', [{
    'name': 'Fix ID9 Companies', 'model_id': model_id, 'state': 'code', 'code': sql,
}])
models.execute_kw(db, uid, password, 'ir.actions.server', 'run', [[action_id]], {'context': ctx})
models.execute_kw(db, uid, password, 'ir.actions.server', 'unlink', [[action_id]])

# Verify
acc = models.execute_kw(db, uid, password, 'account.account', 'read',
    [[9]], {'fields': ['id','name','code','active','company_ids'], 'context': ctx})[0]
print(f"ID 9: {acc['code']} | {acc['name']} | Companies after: {acc['company_ids']}")
