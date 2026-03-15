import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
password = "Amaze@321"
uid = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/common').authenticate(db,'admin',password,{})
models = xmlrpc.client.ServerProxy(url+'/xmlrpc/2/object')
ctx = {'allowed_company_ids': list(range(1,11)), 'active_test': False}

MASTER = 172

# Find all Cash Difference Gain duplicates (exclude master)
all_accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
    [[('name','=','Cash Difference Gain')]],
    {'fields': ['id','name','code','active','company_ids'], 'context': ctx})

DUPLICATE_IDS = [a['id'] for a in all_accs if a['id'] != MASTER]
print(f"Master ID: {MASTER}")
print(f"Duplicate IDs: {DUPLICATE_IDS}")

# Also find any 999103 accounts
accs_999103 = models.execute_kw(db, uid, password, 'account.account', 'search_read',
    [[('code','like','999103')]],
    {'fields': ['id','name','code','active','company_ids'], 'context': ctx})
ids_999103 = [a['id'] for a in accs_999103]
print(f"999103 account IDs: {ids_999103}")
DUPLICATE_IDS = DUPLICATE_IDS + [i for i in ids_999103 if i not in DUPLICATE_IDS and i != MASTER]

print(f"All IDs to consolidate: {DUPLICATE_IDS}")

# Step 1: Add all companies to Master via SQL server action
print(f"\n=== Step 1: Add all companies to Master {MASTER} ===")
model_id = models.execute_kw(db, uid, password, 'ir.model', 'search', [[('model','=','account.account')]])[0]
sql = ("env.cr.execute('INSERT INTO account_account_res_company_rel (account_account_id, res_company_id) "
       "SELECT " + str(MASTER) + ", id FROM res_company "
       "WHERE id NOT IN (SELECT res_company_id FROM account_account_res_company_rel WHERE account_account_id = " + str(MASTER) + ")')")
action_id = models.execute_kw(db, uid, password, 'ir.actions.server', 'create', [{
    'name': f'Fix Master {MASTER} Companies', 'model_id': model_id, 'state': 'code', 'code': sql,
}])
try:
    models.execute_kw(db, uid, password, 'ir.actions.server', 'run', [[action_id]], {'context': ctx})
    print(f"  All companies added to Master {MASTER}.")
except Exception as e:
    print(f"  Error: {e}")
models.execute_kw(db, uid, password, 'ir.actions.server', 'unlink', [[action_id]])

# Step 2: Move lines and delete/archive each duplicate
for acc_id in DUPLICATE_IDS:
    print(f"\n=== Account ID {acc_id} ===")

    line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
        [[('account_id','=',acc_id)]], {'context': ctx})
    if line_ids:
        models.execute_kw(db, uid, password, 'account.move.line', 'write',
            [line_ids, {'account_id': MASTER}], {'context': ctx})
        print(f"  Moved {len(line_ids)} lines to Master {MASTER}.")
    else:
        print(f"  No journal lines.")

    tax_lines = models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'search',
        [[('account_id','=',acc_id)]], {'context': ctx})
    if tax_lines:
        models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'write',
            [tax_lines, {'account_id': MASTER}], {'context': ctx})
        print(f"  Updated {len(tax_lines)} tax repartition lines.")
    else:
        print(f"  No tax repartition lines.")

    try:
        models.execute_kw(db, uid, password, 'account.account', 'unlink', [[acc_id]], {'context': ctx})
        print(f"  Deleted successfully.")
    except Exception as e:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[acc_id], {'active': False}], {'context': ctx})
        print(f"  Archived (cannot delete).")

# Final verification
print("\n=== Final Verification ===")
acc = models.execute_kw(db, uid, password, 'account.account', 'read',
    [[MASTER]], {'fields': ['id','name','code','active','company_ids'], 'context': ctx})[0]
cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
    [[('account_id','=',MASTER)]], {'context': ctx})
print(f"Master ID {MASTER} | {acc['code']} | {acc['name']} | Companies: {acc['company_ids']} | Lines: {cnt}")
print("\nDuplicates:")
for acc_id in DUPLICATE_IDS:
    try:
        a = models.execute_kw(db, uid, password, 'account.account', 'read',
            [[acc_id]], {'fields': ['id','active'], 'context': ctx})[0]
        cnt2 = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id','=',acc_id)]], {'context': ctx})
        print(f"  ID {acc_id} | Active: {a['active']} | Lines: {cnt2}")
    except:
        print(f"  ID {acc_id} | DELETED")
