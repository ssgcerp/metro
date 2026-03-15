import xmlrpc.client
import time

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def get_companies():
    return models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})

def ensure_vat_account(company_id, code, name, acc_type):
    ctx = {'allowed_company_ids': [1, company_id]}
    
    # 1. Check if exists
    existing = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', code), ('company_ids', 'in', [company_id])]],
        {'fields': ['id'], 'context': ctx})
        
    if existing:
        print(f"  [OK] Account {code} exists: {existing[0]['id']}")
        return existing[0]['id']
        
    print(f"  [MISSING] Creating Account {code} ({name})...")
    
    # 2. Get Template info (from any company, e.g. 1)
    # We need account type and reconcile settings
    # We can hardcode specific types if template missing, but better to query
    
    # Use a temporary code to bypass "unique" checks and "required" checks
    # MUST BE ALPHANUMERIC ONLY (No hyphens)
    temp_code = f"{code}C{company_id}TMP"
    
    vals = {
        'name': name,
        'account_type': acc_type, 
        'reconcile': False,
        'company_ids': [(6, 0, [company_id])],
        'code': temp_code 
    }
    
    if code == '104041': # Input
        vals['account_type'] = 'asset_current'
    elif code == '201017': # Output
        vals['account_type'] = 'liability_current'
        
    try:
        new_id = models.execute_kw(db, uid, password, 'account.account', 'create', [vals], {'context': ctx})
        print(f"  [CREATED] ID {new_id} with temp code {temp_code}")
        
        # 3. Update Code
        models.execute_kw(db, uid, password, 'account.account', 'write', [[new_id], {'code': code}], {'context': ctx})
        print(f"  [UPDATED] ID {new_id} code set to {code}")
        return new_id
    except Exception as e:
        print(f"  [ERROR] Creating {code} with temp {temp_code}: {e}")
        return None

def process_lost_entries(company_id, vat_in_id, vat_out_id):
    ctx = {'allowed_company_ids': [1, company_id]}
    
    print("  Checking for lost entries...")
    
    # 1. VAT Output (Sales/Income side) -> Credit entries on Sales/Income accounts?
    # Or just search name='VAT%' and Credit > 0?
    # Let's use the name generic search but filter by Debit/Credit to assign to In/Out
    
    exclude_ids = [vat_in_id, vat_out_id]
    
    # Search ALL lines in this company with VAT in name, not on correct accounts
    domain = [('company_id', '=', company_id), ('name', 'ilike', 'VAT'), ('account_id', 'not in', exclude_ids)]
    
    count = models.execute_kw(db, uid, password, 'account.move.line', 'search_count', [domain], {'context': ctx})
    print(f"  Found {count} potential lost entries.")
    
    if count == 0:
        return

    # Process in batches
    # We should be careful to separate Input vs Output based on Debit/Credit or Account Type
    # But broadly:
    # Debit > 0 -> Input (usually expensive/purchase tax)
    # Credit > 0 -> Output (sales tax)
    # Note: Refunds revers this logic! 
    # But usually 'VAT Input' holds Debits (recoverable) and 'VAT Output' holds Credits (payable).
    # If a Refund happens, Input gets Credit, Output gets Debit.
    # So strictly using Debit/Credit might be risky for refunds.
    # However, if we assume 'VAT Input' account is for Purchases and 'VAT Output' for Sales.
    # If the line is on an Expense account -> Move to Input.
    # If the line is on a Income account -> Move to Output.
    
    # Let's fetch the lines with their account type
    # Since we can't search on joined fields easily in XMLRPC without setup, we iterate.
    
    # Fetch lines
    lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [domain],
        {'fields': ['id', 'name', 'debit', 'credit', 'account_id'], 'limit': 2000, 'context': ctx}) # Increased limit
        
    ids_in = []
    ids_out = []
    skipped_count = 0
    
    # Get all unique account IDs involved
    unique_acc_ids = list(set([l['account_id'][0] for l in lines]))
    if not unique_acc_ids:
        print("  No lines found.")
        return

    # Bulk read account info
    acc_infos = models.execute_kw(db, uid, password, 'account.account', 'read', 
        [unique_acc_ids, ['account_type', 'code', 'name']], {'context': ctx})
    acc_map = {a['id']: a for a in acc_infos}
    
    for l in lines:
        acc = acc_map.get(l['account_id'][0])
        if not acc: continue
        
        atype = acc['account_type']
        
        # SAFETY CHECK: Skip Liquidity (Bank/Cash), Payable, Receivable
        # We only want to move from Expense/Asset (Input) or Income/Liability (Output)
        # Avoid moving Reconciliation, Liquidity, etc.
        if atype in ['asset_cash', 'liability_credit_card', 'equity', 'equity_unaffected', 'payable', 'receivable']:
            skipped_count += 1
            if skipped_count % 100 == 0: print(f"  Skipped {skipped_count} lines (Bank/Payable/etc)...")
            continue
            
        is_input = False
        is_output = False
        
        # Heuristics
        if 'expense' in atype or 'asset' in atype:
            # Likely Input VAT posted to expense
            is_input = True
        elif 'income' in atype:
            # Likely Output VAT posted to income
            is_output = True
        elif 'liability' in atype:
             # Could be either, but usually Output
             if l['credit'] > 0: is_output = True
             elif l['debit'] > 0: is_input = True # Refund?
        else:
             # Fallback
             if l['debit'] > 0: is_input = True
             else: is_output = True
             
        if is_input: ids_in.append(l['id'])
        if is_output: ids_out.append(l['id'])
        
    print(f"  Classified: {len(ids_in)} Input, {len(ids_out)} Output. Skipped: {skipped_count} (Bank/Etc)")
    
    if ids_in and vat_in_id:
        print(f"  Moving {len(ids_in)} lines to VAT Input {vat_in_id} in batches...")
        batch_size = 100
        for i in range(0, len(ids_in), batch_size):
            chunk = ids_in[i:i+batch_size]
            try:
                 models.execute_kw(db, uid, password, 'account.move.line', 'write',
                    [chunk, {'account_id': vat_in_id}], {'context': ctx})
            except Exception as e:
                print(f"  [ERROR] Moving Input Batch {i}: {e}")
            
    if ids_out and vat_out_id:
        print(f"  Moving {len(ids_out)} lines to VAT Output {vat_out_id} in batches...")
        batch_size = 100
        for i in range(0, len(ids_out), batch_size):
            chunk = ids_out[i:i+batch_size]
            try:
                 models.execute_kw(db, uid, password, 'account.move.line', 'write',
                    [chunk, {'account_id': vat_out_id}], {'context': ctx})
            except Exception as e:
                print(f"  [ERROR] Moving Output Batch {i}: {e}")

def run_fix():
    comps = get_companies()
    for c in comps:
        cid = c['id']
        name = c['name']
        print(f"\nProcessing [{cid}] {name}...")
        
        in_id = ensure_vat_account(cid, '104041', 'VAT Input', 'asset_current')
        out_id = ensure_vat_account(cid, '201017', 'VAT Output', 'liability_current')
        
        if in_id and out_id:
            process_lost_entries(cid, in_id, out_id)
        else:
            print("  [SKIP] Skipping entries check due to missing accounts.")

if __name__ == "__main__":
    run_fix()
