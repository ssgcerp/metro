import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def fix_duplicate_vat():
    print("Connecting to Odoo...")
    
    # Constants
    BAD_ACCOUNT_ID = 1259
    GOOD_ACCOUNT_ID = 40
    
    # Verify Bad Account
    bad_acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[BAD_ACCOUNT_ID], ['name', 'code']])
    if not bad_acc:
        print(f"Error: Bad Account {BAD_ACCOUNT_ID} not found.")
        return
    print(f"Bad Account: {bad_acc[0]['name']} (Code: {bad_acc[0]['code']})")
    
    # Verify Good Account
    good_acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[GOOD_ACCOUNT_ID], ['name', 'code']])
    if not good_acc:
        print(f"Error: Good Account {GOOD_ACCOUNT_ID} not found.")
        return
    print(f"Good Account: {good_acc[0]['name']} (Code: {good_acc[0]['code']})")
    
    # Find Journal Items on Bad Account
    lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [[('account_id', '=', BAD_ACCOUNT_ID)]],
        {'fields': ['id', 'name']})
        
    print(f"\nFound {len(lines)} lines on Bad Account:")
    for l in lines:
        print(f" - Line {l['id']}: {l['name']}")
        
    if not lines:
        print("No lines to fix.")
    else:
        # Move lines to Good Account
        line_ids = [l['id'] for l in lines]
        print(f"\nMoving lines... Testing on first line {line_ids[0]}")
        
        try:
            # Try to write to NAME first to check permissions
            print("Attempting to update name...")
            models.execute_kw(db, uid, password, 'account.move.line', 'write',
                [[line_ids[0]], {'name': 'VAT BF Updated'}],
                {'context': {'check_move_validity': False}})
            print("Success! One line name updated.")
            
            # Now try account_id
            print("Attempting to update account_id...")
            models.execute_kw(db, uid, password, 'account.move.line', 'write',
                [[line_ids[0]], {'account_id': GOOD_ACCOUNT_ID}],
                {'context': {'check_move_validity': False}})
            print("Success! Account ID updated.")
            
        except Exception as e:
            print(f"Error moving lines: {e}") 
            return

    # Archive Bad Account
    print(f"\nArchiving Bad Account {BAD_ACCOUNT_ID}...")
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[BAD_ACCOUNT_ID], {'active': False, 'name': 'VAT Input (Duplicate - Archived)'}])
        print("Success! Account archived.")
    except Exception as e:
        print(f"Error archiving account: {e}")

if __name__ == "__main__":
    fix_duplicate_vat()
