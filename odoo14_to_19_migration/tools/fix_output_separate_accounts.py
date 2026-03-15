import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def fix_separate():
    print(f"--- Fixing VAT Output (Separate Accounts) ---")
    
    targets = [2, 3, 5, 8] # RAK, Dubai, Ajman, Mysore
    
    for cid in targets:
        print(f"\nProcessing Company {cid}...")
        ctx = {'allowed_company_ids': [1, cid]}
        
        # 1. Check for ANY account with code 201017 (Main Candidate)
        main = models.execute_kw(db, uid, password, 'account.account', 'search_read',
            [[('code', '=', '201017'), ('company_ids', 'in', [cid])]],
            {'fields': ['id', 'name', 'code'], 'context': ctx})
            
        main_id = None
        if main:
            main_id = main[0]['id']
            print(f"  Found existing Main: {main[0]}")
            # Ensure name is generic
            if main[0]['name'] != 'VAT Output':
                models.execute_kw(db, uid, password, 'account.account', 'write',
                    [[main_id], {'name': 'VAT Output'}], {'context': ctx})
                print("  Updated name to 'VAT Output'")
        else:
            # 2. Try to find one of the TMP ones to promote
            tmps = models.execute_kw(db, uid, password, 'account.account', 'search_read',
                [[('code', 'like', '201017'), ('company_ids', 'in', [cid])]],
                {'fields': ['id', 'name', 'code'], 'context': ctx})
                
            if tmps:
                # Use the first one
                cand = tmps[0]
                main_id = cand['id']
                print(f"  Promoting TMP to Main: {cand}")
                try:
                    models.execute_kw(db, uid, password, 'account.account', 'write',
                        [[main_id], {'code': '201017', 'name': 'VAT Output'}],
                        {'context': ctx})
                    print("  Success. Promoted to 201017.")
                except Exception as e:
                    print(f"  Error promoting: {e}")
            else:
                # Create New
                print("  Creating NEW 201017 account...")
                try:
                    main_id = models.execute_kw(db, uid, password, 'account.account', 'create',
                        [{'code': '201017', 'name': 'VAT Output', 'account_type': 'liability_current', 'company_ids': [(4, cid)]}],
                        {'context': ctx})
                    print(f"  Created ID {main_id}")
                except Exception as e:
                    print(f"  Creation failed: {e}")
                    continue

        # 3. Merge any specific company duplicates into Main
        if main_id:
            dups = models.execute_kw(db, uid, password, 'account.account', 'search_read',
                [[('code', 'like', '201017'), ('id', '!=', main_id), ('company_ids', 'in', [cid])]],
                {'fields': ['id', 'name', 'code'], 'context': ctx})
             
            # Also catch 'VAT Output' by name if code is weird
            dups2 = models.execute_kw(db, uid, password, 'account.account', 'search_read',
                [[('name', 'ilike', 'VAT Output'), ('id', '!=', main_id), ('company_ids', 'in', [cid]), ('code', '!=', '201017')]],
                 {'fields': ['id', 'name', 'code'], 'context': ctx})
            
            all_dups = dups + dups2
            # Dedup list by ID
            unique_dups = {d['id']: d for d in all_dups}.values()

            for dup in unique_dups:
                print(f"  Merging Duplicate: {dup}")
                # Move Lines
                line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search',
                    [[('account_id', '=', dup['id'])]], {'context': ctx})
                
                if line_ids:
                    print(f"    Moving {len(line_ids)} lines...")
                    try:
                        models.execute_kw(db, uid, password, 'account.move.line', 'write',
                            [line_ids, {'account_id': main_id}], {'context': ctx})
                    except Exception as e:
                        print(f"    Error moving lines: {e}")
                
                # Archive
                new_code = f"201017C{cid}OLD_{dup['id']}"
                print(f"    Archiving as {new_code}...")
                try:
                    models.execute_kw(db, uid, password, 'account.account', 'write',
                        [[dup['id']], {'active': False, 'code': new_code}],
                        {'context': ctx})
                except Exception as e:
                    print(f"    Error archiving: {e}")

if __name__ == "__main__":
    fix_separate()
