import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metro"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def calculate_balance_and_fix():
    print("Connecting to Odoo...")
    
    BAD_ACCOUNT_ID = 1259
    GOOD_ACCOUNT_ID = 40
    
    # Verify Bad Account
    # company_id is missing, use company_ids
    bad_acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[BAD_ACCOUNT_ID], ['name', 'code', 'company_ids']])
    if not bad_acc:
        print(f"Error: Bad Account {BAD_ACCOUNT_ID} not found.")
        return
    print(f"Bad Account: {bad_acc[0]['name']} (Company IDs: {bad_acc[0].get('company_ids')})")
    
    # Verify Good Account
    good_acc = models.execute_kw(db, uid, password, 'account.account', 'read', [[GOOD_ACCOUNT_ID], ['name', 'code', 'company_ids']])
    if not good_acc:
        print(f"Error: Good Account {GOOD_ACCOUNT_ID} not found.")
        return
    print(f"Good Account: {good_acc[0]['name']} (Code: {good_acc[0]['code']}, Company IDs: {good_acc[0].get('company_ids')})")
    
    # Read lines and their company (Lines usually have company_id, not company_ids)
    lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [[('account_id', '=', BAD_ACCOUNT_ID), ('parent_state', '=', 'posted')]],
        {'fields': ['id', 'name', 'debit', 'credit', 'company_id']})
        
    balance = 0.0
    target_company_id = None
    
    print(f"Found {len(lines)} posted lines:")
    for l in lines:
        net = l['debit'] - l['credit']
        balance += net
        print(f" - Line {l['id']}: {l['name']} | Dr: {l['debit']} | Cr: {l['credit']} | Net: {net} | Comp: {l['company_id']}")
        if l['company_id']:
            target_company_id = l['company_id'][0] # (ID, Name) tuple

    print(f"\nTotal Balance on Account {BAD_ACCOUNT_ID}: {balance}")
    print(f"Target Company ID: {target_company_id}")
    
    if abs(balance) < 0.01:
        print("Balance is zero. No adjustment needed. Proceeding to archive.")
        create_adjustment_entry = False
    else:
        print(f"Adjustment needed: {balance}")
        create_adjustment_entry = True
        
    # Check if Good Account is compatible
    good_allowed = False
    good_company_ids = good_acc[0].get('company_ids', [])
    if not good_company_ids:
        good_allowed = True # Shared
    elif target_company_id in good_company_ids:
        good_allowed = True
        
    if not good_allowed:
        print(f"Warning: Good Account {GOOD_ACCOUNT_ID} is not allowed for Company {target_company_id}!")
        # Search for better account
         # Try finding by code first (more reliable)
        domain = [('code', '=', '104041'), '|', ('company_ids', '=', False), ('company_ids', 'in', [target_company_id])]
        good_acc_ids = models.execute_kw(db, uid, password, 'account.account', 'search', [domain])
            
        if not good_acc_ids:
            # Try by name
            domain = [('name', 'ilike', 'VAT Input'), '|', ('company_ids', '=', False), ('company_ids', 'in', [target_company_id]), ('id', '!=', BAD_ACCOUNT_ID)]
            good_acc_ids = models.execute_kw(db, uid, password, 'account.account', 'search', [domain])
                
        if good_acc_ids:
            GOOD_ACCOUNT_ID = good_acc_ids[0]
            print(f"Refined Good Account ID: {GOOD_ACCOUNT_ID} for Company {target_company_id}")
        else:
            print(f"Error: Could not find a suitable Good Account in company {target_company_id}.")
            return
    else:
        print(f"Good Account {GOOD_ACCOUNT_ID} is compatible.")



    # Find Journal (General) for the correct company
    domain = [('type', '=', 'general')]
    if target_company_id:
        domain.append(('company_id', '=', target_company_id))
        
    journal_id = models.execute_kw(db, uid, password, 'account.journal', 'search', [domain])
    if not journal_id:
        print(f"Error: No General Journal found for company {target_company_id}.")
        return
    journal_id = journal_id[0]
    
    # Read journal info (careful with fields)
    j_data = models.execute_kw(db, uid, password, 'account.journal', 'read', [[journal_id], ['name', 'company_id']])
    print(f"Using Journal: {j_data[0]['name']} (Company: {j_data[0]['company_id']})")


    if create_adjustment_entry:
        print("Creating Adjustment Entry...")
        
        # If balance is positive (Debit), we need to Credit Bad Account.
        # Line 1: Bad Account, Credit = Balance, Debit = 0
        # Line 2: Good Account, Debit = Balance, Credit = 0
        
        # If balance is negative (Credit), we need to Debit Bad Account.
        # ...
        
        if balance > 0:
            credit_bad = balance
            debit_bad = 0.0
            debit_good = balance
            credit_good = 0.0
        else:
            credit_bad = 0.0
            debit_bad = abs(balance)
            debit_good = 0.0
            credit_good = abs(balance)
            
        move_vals = {
            'date': '2026-02-16', # Or current date
            'journal_id': journal_id,
            'company_id': target_company_id, # EXPLICITLY SET COMPANY
            'ref': 'Fix Duplicate VAT Input Account',
            'line_ids': [
                (0, 0, {
                    'account_id': BAD_ACCOUNT_ID,
                    'name': 'Transfer Balance from Duplicate Account',
                    'debit': debit_bad,
                    'credit': credit_bad,
                    'company_id': target_company_id, # Explicit on line too
                }),
                (0, 0, {
                    'account_id': GOOD_ACCOUNT_ID,
                    'name': 'Transfer Balance from Duplicate Account',
                    'debit': debit_good,
                    'credit': credit_good,
                    'company_id': target_company_id, # Explicit on line too
                })
            ]
        }
        
        try:
            # Pass company in context to ensure correct environment
            ctx = {'company_id': target_company_id}
            
            print(f"Creating move with context: {ctx}")
            move_id = models.execute_kw(db, uid, password, 'account.move', 'create', [move_vals], {'context': ctx})
            print(f"Created Move ID: {move_id}")
            
            # Post it
            models.execute_kw(db, uid, password, 'account.move', 'action_post', [[move_id]], {'context': ctx})
            print("Move Posted.")
            
        except Exception as e:
            print(f"Error creating move: {e}")
            return

    # Archive
    print("Archiving Bad Account...")
    try:
        models.execute_kw(db, uid, password, 'account.account', 'write',
            [[BAD_ACCOUNT_ID], {'active': False, 'name': 'VAT Input (Duplicate - Archived)'}])
        print("Success! Account Archived.")
    except Exception as e:
        print(f"Error archiving: {e}")

if __name__ == "__main__":
    calculate_balance_and_fix()
