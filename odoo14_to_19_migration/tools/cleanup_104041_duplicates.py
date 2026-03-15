import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

ctx = {'allowed_company_ids': list(range(1, 11)), 'active_test': False}
MASTER = 744

# Find all 104041 accounts except master
accs = models.execute_kw(db, uid, password, 'account.account', 'search_read',
    [[('code', 'like', '104041'), ('id', '!=', MASTER)]],
    {'fields': ['id', 'name', 'code', 'active'], 'context': ctx})

print(f"Found {len(accs)} duplicate accounts to clean up:")

for a in accs:
    acc_id = a['id']
    acc_name = a['name']
    
    # Check lines
    cnt = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id', '=', acc_id)]], {'context': ctx})
    print(f"\n  ID {acc_id} | {acc_name} | Active: {a['active']} | Lines: {cnt}")

    # Move lines if any
    if cnt > 0:
        line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
            [[('account_id', '=', acc_id)]], {'context': ctx})
        models.execute_kw(db, uid, password, 'account.move.line', 'write',
            [line_ids, {'account_id': MASTER}], {'context': ctx})
        print(f"    -> Moved {cnt} lines to Master 744")

    # Try delete
    try:
        models.execute_kw(db, uid, password, 'account.account', 'unlink',
            [[acc_id]], {'context': ctx})
        print(f"    -> Deleted successfully")
    except Exception as e:
        print(f"    -> Cannot delete, trying archive: {e}")
        try:
            models.execute_kw(db, uid, password, 'account.account', 'write',
                [[acc_id], {'active': False}], {'context': ctx})
            print(f"    -> Archived")
        except Exception as e2:
            print(f"    -> Archive also failed: {e2}")

print("\n=== Done! ===")

# Final check
master = models.execute_kw(db, uid, password, 'account.account', 'read',
    [[MASTER]], {'fields': ['name', 'code', 'company_ids'], 'context': ctx})
line_count = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
    [[('account_id', '=', MASTER)]], {'context': ctx})
print(f"\nMaster 744: Companies={master[0]['company_ids']}, Lines={line_count}")
