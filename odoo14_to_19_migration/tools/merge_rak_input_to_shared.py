import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def merge_rak():
    print(f"--- Merging RAK Input 1764 -> Shared 744 ---")
    
    # IDs
    BAD_ID = 1764
    GOOD_ID = 744
    RAK_ID = 2
    
    ctx = {'allowed_company_ids': [1, RAK_ID]}
    
    # 1. Check Bad Account
    bad = models.execute_kw(db, uid, password, 'account.account', 'read', [[BAD_ID], ['code', 'name']], {'context': ctx})
    if not bad:
        print("Bad account 1764 not found!")
        return
    print(f"Bad Account: {bad}")
    
    # 2. Check Good Account
    good = models.execute_kw(db, uid, password, 'account.account', 'read', [[GOOD_ID], ['code', 'name', 'company_ids']], {'context': ctx})
    if not good:
        print("Good account 744 not found!")
        return
    print(f"Good Account: {good}")
    
    # 3. Move Lines
    lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [[('account_id', '=', BAD_ID)]],
        {'fields': ['id', 'name'], 'context': ctx})
        
    print(f"Found {len(lines)} lines on Bad Account.")
    
    if lines:
        ids = [l['id'] for l in lines]
        print(f"Moving {len(ids)} lines to ID {GOOD_ID}...")
        
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            chunk = ids[i:i+batch_size]
            try:
                models.execute_kw(db, uid, password, 'account.move.line', 'write',
                    [chunk, {'account_id': GOOD_ID}],
                    {'context': ctx})
            except Exception as e:
                print(f"Error moving batch {i}: {e}")
                
    # 4. Archive Bad Account
    print("Archiving Bad Account 1764...")
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[BAD_ID], {'active': False, 'code': '104041RAK-ARCHIVED', 'name': 'VAT Input (RAK) [ARCHIVED]'}],
            {'context': ctx})
        print("Success! Bad account archived.")
    except Exception as e:
        print(f"Error archiving: {e}")

if __name__ == "__main__":
    merge_rak()
