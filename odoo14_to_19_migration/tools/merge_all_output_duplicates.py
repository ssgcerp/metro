import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def merge_all_outputs():
    print(f"--- Merging All Output Duplicates to Shared 1761 ---")
    
    MASTER_ID = 1761
    target_companies = [2, 3, 5, 8] # RAK, Dubai, Ajman, Mysore
    
    # 0. PRE-STEP: Rename Duplicates to free up the code
    print("Pre-step: Renaming duplicates to avoid uniqueness constraint...")
    for cid in target_companies:
        if cid == 2: continue # Master is RAK
        ctx = {'allowed_company_ids': [1, cid]}
        # Find duplicates by code
        dups = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', 'like', '201017'), ('id', '!=', MASTER_ID), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
        
        for dup in dups:
            print(f"  [Company {cid}] Renaming ID {dup['id']} ({dup['code']}) to TMP...")
            new_code = f"201017C{cid}TMP"
            try:
                models.execute_kw(db, uid, password, 'account.account', 'write',
                    [[dup['id']], {'code': new_code}], {'context': ctx})
            except Exception as e:
                print(f"  Error renaming: {e}")

    # 1. Update Master Account (Add companies)
    ctx_master = {'allowed_company_ids': [1, 2, 3, 5, 8]}
    print(f"\nUpdating Master Account {MASTER_ID} to include companies {target_companies}...")
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[MASTER_ID], {'company_ids': [(6, 0, target_companies)], 'name': 'VAT Output', 'code': '201017'}],
            {'context': ctx_master})
        print("  Success. Master account updated.")
    except Exception as e:
        print(f"  Error updating master: {e}")
        return

    # 2. Process Duplicates (Move Lines & Archive)
    for cid in target_companies:
        if cid == 2: continue 
        
        print(f"\nProcessing Company {cid}...")
        ctx = {'allowed_company_ids': [1, cid]}
        
        # Search for the accounts we just renamed (or any with duplicate names)
        # Search by code TMP or Name
        dups = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', 'like', 'TMP'), ('id', '!=', MASTER_ID), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
             
        for dup in dups:
            dup_id = dup['id']
            print(f"  Found Duplicate: ID {dup_id} | {dup['code']} | {dup['name']}")
            
            # Move Lines
            lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
                [[('account_id', '=', dup_id)]], {'context': ctx})
            print(f"    Lines to move: {lines}")
            
            if lines > 0:
                print("    Moving lines...")
                line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
                    [[('account_id', '=', dup_id)]], {'context': ctx})
                
                batch_size = 100
                for i in range(0, len(line_ids), batch_size):
                    chunk = line_ids[i:i+batch_size]
                    try:
                        models.execute_kw(db, uid, password, 'account.move.line', 'write',
                            [chunk, {'account_id': MASTER_ID}], {'context': ctx})
                    except Exception as e:
                        print(f"    Error moving batch: {e}")
                        
            # Archive
            new_code = f"201017C{cid}OLD"
            old_name = f"{dup['name']} [ARCHIVED]" 
            print(f"    Archiving as {new_code}...")
            try:
                models.execute_kw(db, uid, password, 'account.account', 'write',
                    [[dup_id], {'active': False, 'code': new_code, 'name': old_name}],
                    {'context': ctx})
                print("    Archived.")
            except Exception as e:
                print(f"    Error archiving: {e}")

if __name__ == "__main__":
    merge_all_outputs()
