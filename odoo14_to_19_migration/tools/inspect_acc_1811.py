import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def inspect():
    print(f"--- Inspecting Account 1811 ---")
    
    # Read Account
    acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[1811]], {'fields': ['name', 'code', 'company_ids']})
    print(f"Account: {acc}")
    
    if not acc:
        print("Account 1811 not found!")
        return

    company_ids = acc[0]['company_ids']
    print(f"Account Company IDs: {company_ids}")
    
    # Read Lines
    print("--- Inspecting Lines ---")
    lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [[('account_id', '=', 1811)]], 
        {'fields': ['name', 'company_id', 'move_id', 'parent_state'], 'limit': 10})
        
    for l in lines:
        print(f"Line ID {l['id']} | Move {l['move_id']} | Company {l['company_id']} | State {l['parent_state']}")
        
    # Check if there are lines with company_id NOT in account's company_ids
    # Note: search domain for 'active_test' might be needed if companies are archived? No.
    # We want to find lines where company_id is NOT in company_ids
    
    primary_company = company_ids[0] if company_ids else False
    if primary_company:
        print(f"Checking for lines NOT in Company {primary_company}...")
        
        # 1. Check Line Company
        count_diff = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
            [[('account_id', '=', 1811), ('company_id', '!=', primary_company)]])
        print(f"Lines with DIFFERENT Company ID: {count_diff}")
        
        # 2. Check Parent Move Company
        # Get all lines
        line_ids = models.execute_kw(db, uid, password, 'account.move.line', 'search', [[('account_id', '=', 1811)]])
        if line_ids:
             # Batch read moves
             lines_data = models.execute_kw(db, uid, password, 'account.move.line', 'read', [line_ids], {'fields': ['move_id', 'journal_id']})
             move_ids = list(set(l['move_id'][0] for l in lines_data if l['move_id']))
             journal_ids = list(set(l['journal_id'][0] for l in lines_data if l['journal_id']))
             
             print(f"Checking {len(move_ids)} Moves for Company mismatch...")
             count_move_diff = models.execute_kw(db, uid, password, 'account.move', 'search_count',
                [[('id', 'in', move_ids), ('company_id', '!=', primary_company)]])
             print(f"Moves with DIFFERENT Company ID: {count_move_diff}")
             
             print(f"Checking {len(journal_ids)} Journals for Company mismatch...")
             count_journal_diff = models.execute_kw(db, uid, password, 'account.journal', 'search_count',
                [[('id', 'in', journal_ids), ('company_id', '!=', primary_company)]])
             print(f"Journals with DIFFERENT Company ID: {count_journal_diff}")
        
    else:
        print("Account has no company_ids!")

if __name__ == "__main__":
    inspect()
