import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def merge_all_inputs():
    print(f"--- Merging All Input Duplicates to Shared 744 ---")
    
    MASTER_ID = 744
    # All companies found: 1=AUH, 2=RAK, 3=DXB, 4=SHJ, 5=AJM, 6=FUJ, 7=DXBS, 8=MYS, 9=ENV, 10=BOSS
    target_companies = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] 
    
    # 1. Check Master
    # Need to check as admin with broad context
    ctx_master = {'allowed_company_ids': target_companies}
    master = models.execute_kw(db, uid, password, 'account.account', 'read', [[MASTER_ID], ['code', 'name', 'company_ids']], {'context': ctx_master})
    if not master:
        print("Master account 744 not found!")
        return
    print(f"Master Account: {master}")
    
    for cid in target_companies:
        print(f"\nProcessing Company {cid}...")
        # Use ALL companies in context to avoid cross-company access errors
        ctx = {'allowed_company_ids': target_companies}
        
        # Find duplicated accounts (should be 104041 code but NOT ID 744)
        dups = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', 'like', '104041'), ('id', '!=', MASTER_ID), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code', 'company_ids'], 'context': ctx})
            
        for dup in dups:
            dup_id = dup['id']
            print(f"  Found Duplicate: ID {dup_id} | {dup['code']} | {dup['name']}")
            
            # Move Lines
            lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
                [[('account_id', '=', dup_id)]], {'context': ctx})
            print(f"    Lines to move: {lines}")
            
            if lines > 0:
                print("    Moving lines...")
                # Fetch IDs 
                line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
                    [[('account_id', '=', dup_id)]], {'context': ctx})
                
                # Move in batches
                batch_size = 100
                for i in range(0, len(line_ids), batch_size):
                    chunk = line_ids[i:i+batch_size]
                    try:
                        models.execute_kw(db, uid, password, 'account.move.line', 'write',
                            [chunk, {'account_id': MASTER_ID}], {'context': ctx})
                    except Exception as e:
                        print(f"    Error moving batch: {e}")
                        
            # Archive
            new_code = f"104041C{cid}OLD" # Alphanumeric only
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
    merge_all_inputs()
