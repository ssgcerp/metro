import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
password = "Amaze@321"
uid = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common').authenticate(db, 'admin', password, {})
models = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')

ctx = {'allowed_company_ids': list(range(1, 11)), 'active_test': False}
MASTER = 1086
TARGET_IDS = [1229, 498, 890, 714]

for acc_id in TARGET_IDS:
    print(f"\n=== Account ID {acc_id} ===")

    # 1. Check and move journal lines
    line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
        [[('account_id', '=', acc_id)]], {'context': ctx})
    if line_ids:
        models.execute_kw(db, uid, password, 'account.move.line', 'write',
            [line_ids, {'account_id': MASTER}], {'context': ctx})
        print(f"  Moved {len(line_ids)} journal lines to 744")
    else:
        print(f"  No journal lines")

    # 2. Check and update tax repartition lines
    tax_lines = models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'search',
        [[('account_id', '=', acc_id)]], {'context': ctx})
    if tax_lines:
        models.execute_kw(db, uid, password, 'account.tax.repartition.line', 'write',
            [tax_lines, {'account_id': MASTER}], {'context': ctx})
        print(f"  Updated {len(tax_lines)} tax repartition lines to 744")
    else:
        print(f"  No tax repartition lines")

    # 3. Delete
    try:
        models.execute_kw(db, uid, password, 'account.account', 'unlink',
            [[acc_id]], {'context': ctx})
        print(f"  Deleted successfully")
    except Exception as e:
        print(f"  Cannot delete, archiving: {e}")
        try:
            models.execute_kw(db, uid, password, 'account.account', 'write',
                [[acc_id], {'active': False}], {'context': ctx})
            print(f"  Archived")
        except Exception as e2:
            print(f"  Archive also failed: {e2}")

print("\n=== All done! ===")
