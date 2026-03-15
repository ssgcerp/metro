import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def move_vat_input():
    RAK_ID = 2
    ctx = {'allowed_company_ids': [1, RAK_ID]}
    
    NEW_INPUT_ID = 1764
    EXCLUDE_IDS = [1764, 1761, 40, 70] # Don't move if already on VAT accounts (RAK or Shared)
    
    print("Searching for misplaced VAT Input lines...")
    
    # Search for lines to move
    # Criteria: RAK company, Name has 'VAT', Start with 'VAT', Debit > 0, Not already on VAT accounts
    # 'VAT %' usually indicates tax line
    lines_to_move = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [[('company_id', '=', RAK_ID), ('name', 'ilike', 'VAT'), ('debit', '>', 0), ('account_id', 'not in', EXCLUDE_IDS)]],
        {'fields': ['id', 'name', 'debit', 'account_id'], 'context': ctx})
        
    print(f"Found {len(lines_to_move)} VAT Input lines on Wrong Accounts.")
    
    if lines_to_move:
        ids_to_move = [l['id'] for l in lines_to_move]
        print(f"Moving {len(ids_to_move)} lines to VAT Input (ID {NEW_INPUT_ID})...")
        
        # Process in batches of 100 to avoid timeouts
        batch_size = 100
        for i in range(0, len(ids_to_move), batch_size):
            batch_ids = ids_to_move[i:i + batch_size]
            print(f"Processing batch {i} to {i+batch_size}...")
            try:
                 models.execute_kw(db, uid, password, 'account.move.line', 'write',
                    [batch_ids, {'account_id': NEW_INPUT_ID}],
                    {'context': ctx})
            except Exception as e:
                print(f"Error moving batch {i}: {e}")
        
        print("Done.")

if __name__ == "__main__":
    move_vat_input()
