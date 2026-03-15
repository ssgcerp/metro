import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
password = "Amaze@321"
uid = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common').authenticate(db, 'admin', password, {})
models = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')

ctx = {'allowed_company_ids': list(range(1, 11)), 'active_test': False}
MASTER = 1086   # 102000 Accounts Receivable (correct one)
OLD_ID = 10     # 102011 ABU DHABI duplicate to remove

# === Step 1: Audit both accounts ===
print("=== Step 1: Audit ===")
for aid in [MASTER, OLD_ID]:
    acc = models.execute_kw(db, uid, password, 'account.account', 'read',
        [[aid]], {'fields': ['id', 'name', 'code', 'active', 'company_ids'], 'context': ctx})[0]
    cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id', '=', aid)]], {'context': ctx})
    print(f"  ID {acc['id']} | {acc['code']} | {acc['name']} | Active: {acc['active']} | Companies: {acc['company_ids']} | Lines: {cnt}")

# === Step 2: Add ABU DHABI (company 1) to Master 1086 via SQL ===
print("\n=== Step 2: Add ABU DHABI company to Master 1086 ===")
model_id = models.execute_kw(db, uid, password, 'ir.model', 'search', [[('model', '=', 'account.account')]])[0]
sql_code = (
    "env.cr.execute('INSERT INTO account_account_res_company_rel (account_account_id, res_company_id) "
    "SELECT 1086, id FROM res_company "
    "WHERE id NOT IN (SELECT res_company_id FROM account_account_res_company_rel WHERE account_account_id = 1086)')"
)
action_id = models.execute_kw(db, uid, password, 'ir.actions.server', 'create', [{
    'name': 'Fix 1086 Companies', 'model_id': model_id, 'state': 'code', 'code': sql_code,
}])
try:
    models.execute_kw(db, uid, password, 'ir.actions.server', 'run', [[action_id]], {'context': ctx})
    print("  ABU DHABI company added to Master 1086.")
except Exception as e:
    print(f"  Error: {e}")
models.execute_kw(db, uid, password, 'ir.actions.server', 'unlink', [[action_id]])

# === Step 3: Move all journal lines from ID 10 to Master 1086 ===
print("\n=== Step 3: Move journal lines from ID 10 to 1086 ===")
line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
    [[('account_id', '=', OLD_ID)]], {'context': ctx})
if line_ids:
    batch_size = 200
    moved = 0
    for i in range(0, len(line_ids), batch_size):
        chunk = line_ids[i:i+batch_size]
        models.execute_kw(db, uid, password, 'account.move.line', 'write',
            [chunk, {'account_id': MASTER}], {'context': ctx})
        moved += len(chunk)
        print(f"  Moved {moved}/{len(line_ids)}...", end='\r')
    print(f"\n  Done. Moved {moved} lines to 1086.")
else:
    print("  No journal lines to move.")

# === Step 4: Update tax repartition lines ===
print("\n=== Step 4: Update tax repartition lines ===")
tax_lines = models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'search',
    [[('account_id', '=', OLD_ID)]], {'context': ctx})
if tax_lines:
    models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'write',
        [tax_lines, {'account_id': MASTER}], {'context': ctx})
    print(f"  Updated {len(tax_lines)} tax repartition lines to 1086.")
else:
    print("  No tax repartition lines.")

# === Step 5: Verify then delete ID 10 ===
print("\n=== Step 5: Verify and delete ID 10 ===")
remaining = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
    [[('account_id', '=', OLD_ID)]], {'context': ctx})
print(f"  Remaining lines on ID 10: {remaining}")
if remaining == 0:
    try:
        models.execute_kw(db, uid, password, 'account.account', 'unlink', [[OLD_ID]], {'context': ctx})
        print("  ID 10 deleted successfully.")
    except Exception as e:
        print(f"  Cannot delete, archiving: {e}")
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[OLD_ID], {'active': False}], {'context': ctx})
        print("  ID 10 archived.")
else:
    print("  WARNING: Lines still remain, not deleting.")

# === Final Audit ===
print("\n=== Final Audit ===")
acc = models.execute_kw(db, uid, password, 'account.account', 'read',
    [[MASTER]], {'fields': ['id', 'name', 'code', 'active', 'company_ids'], 'context': ctx})[0]
cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
    [[('account_id', '=', MASTER)]], {'context': ctx})
print(f"  Master ID {MASTER} | {acc['code']} | Companies: {acc['company_ids']} | Lines: {cnt}")
