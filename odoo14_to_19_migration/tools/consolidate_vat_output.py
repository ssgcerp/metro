import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
password = "Amaze@321"
uid = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common').authenticate(db, 'admin', password, {})
models = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')

ctx = {'allowed_company_ids': list(range(1, 11)), 'active_test': False}
MASTER = 70
CODE = '201017'

# === Step 1: Find all 201017 accounts ===
print(f"=== Step 1: Audit all {CODE} accounts ===")
accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
    [[('code', 'like', CODE)]],
    {'fields': ['id', 'name', 'code', 'active', 'company_ids'], 'context': ctx})

master = next((a for a in accs if a['id'] == MASTER), None)
others = [a for a in accs if a['id'] != MASTER]
print(f"Master (ID {MASTER}): {master['name']} | Companies: {master['company_ids']}")
print(f"Duplicates to merge: {len(others)}")
for a in others:
    cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id', '=', a['id'])]], {'context': ctx})
    print(f"  ID {a['id']} | {a['name']} | Active: {a['active']} | Lines: {cnt}")

# === Step 2: Add all companies to Master 70 via server action SQL ===
print(f"\n=== Step 2: Add all companies to Master {MASTER} ===")
code_add = (
    f"env.cr.execute('INSERT INTO account_account_res_company_rel (account_account_id, res_company_id) "
    f"SELECT {MASTER}, id FROM res_company "
    f"WHERE id NOT IN (SELECT res_company_id FROM account_account_res_company_rel WHERE account_account_id = {MASTER})')"
)
model_id = models.execute_kw(db, uid, password, 'ir.model', 'search', [[('model', '=', 'account.account')]])[0]
action_id = models.execute_kw(db, uid, password, 'ir.actions.server', 'create', [{
    'name': 'Fix 70 Companies', 'model_id': model_id, 'state': 'code', 'code': code_add,
}])
try:
    models.execute_kw(db, uid, password, 'ir.actions.server', 'run', [[action_id]], {'context': ctx})
    print("  Companies added successfully.")
except Exception as e:
    print(f"  Error: {e}")
models.execute_kw(db, uid, password, 'ir.actions.server', 'unlink', [[action_id]])

# === Step 3: For each duplicate, move lines + tax refs, then delete ===
print(f"\n=== Step 3: Process each duplicate ===")
for a in others:
    acc_id = a['id']
    print(f"\n  --- ID {acc_id} | {a['name']} ---")

    # Move journal lines
    line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
        [[('account_id', '=', acc_id)]], {'context': ctx})
    if line_ids:
        batch_size = 200
        moved = 0
        for i in range(0, len(line_ids), batch_size):
            chunk = line_ids[i:i+batch_size]
            models.execute_kw(db, uid, password, 'account.move.line', 'write',
                [chunk, {'account_id': MASTER}], {'context': ctx})
            moved += len(chunk)
        print(f"    Moved {moved} journal lines to {MASTER}")
    else:
        print(f"    No journal lines")

    # Update tax repartition lines
    tax_lines = models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'search',
        [[('account_id', '=', acc_id)]], {'context': ctx})
    if tax_lines:
        models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'write',
            [tax_lines, {'account_id': MASTER}], {'context': ctx})
        print(f"    Updated {len(tax_lines)} tax repartition lines to {MASTER}")
    else:
        print(f"    No tax repartition lines")

    # Delete
    try:
        models.execute_kw(db, uid, password, 'account.account', 'unlink',
            [[acc_id]], {'context': ctx})
        print(f"    Deleted successfully")
    except Exception as e:
        print(f"    Cannot delete, archiving: {e}")
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[acc_id], {'active': False}], {'context': ctx})
        print(f"    Archived")

# === Step 4: Final verification ===
print(f"\n=== Step 4: Final Verification ===")
remaining = models.execute_kw(db, uid, password, 'account.account', 'search_read',
    [[('code', 'like', CODE)]],
    {'fields': ['id', 'name', 'code', 'active', 'company_ids'], 'context': ctx})
for a in remaining:
    cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id', '=', a['id'])]], {'context': ctx})
    print(f"  ID {a['id']} | {a['name']} | Active: {a['active']} | Companies: {a['company_ids']} | Lines: {cnt}")
