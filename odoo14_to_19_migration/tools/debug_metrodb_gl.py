import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def debug_gl_entries():
    print(f"--- Searching for VAT Entries in {db} / RAK (ID 2) ---")
    
    RAK_ID = 2
    ctx = {'allowed_company_ids': [1, RAK_ID]}
    
    # 1. Check if ANY entries exist on the new accounts
    new_input_id = 1764  # From previous step output
    new_output_id = 1761 # From previous step output
    
    count_in = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id', '=', new_input_id), ('company_id', '=', RAK_ID)]], {'context': ctx})
    print(f"Entries on New VAT Input ({new_input_id}): {count_in}")
    
    count_out = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id', '=', new_output_id), ('company_id', '=', RAK_ID)]], {'context': ctx})
    print(f"Entries on New VAT Output ({new_output_id}): {count_out}")

    # 2. Search for entries named 'VAT' on ANY account in RAK
    print("\n--- Searching for misplaced 'VAT' entries ---")
    lost_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [[('company_id', '=', RAK_ID), ('name', 'ilike', 'VAT'), ('account_id', 'not in', [new_input_id, new_output_id])]],
        {'fields': ['id', 'name', 'account_id', 'date', 'move_id'], 'limit': 20, 'context': ctx})
        
    if lost_lines:
        print(f"Found {len(lost_lines)} potential VAT lines on WRONG accounts:")
        for l in lost_lines:
            acc_name = models.execute_kw(db, uid, password, 'account.account', 'read', 
                [[l['account_id'][0]], ['name', 'code']], {'context': ctx})
            acc_str = f"[{acc_name[0]['code']}] {acc_name[0]['name']}" if acc_name else "Unknown"
            print(f" - Date: {l['date']} | Desc: {l['name']} | On Account: {acc_str}")
    else:
        print("No lines with 'VAT' in name found on other accounts.")

    # 3. Check Account 40 (Metro VAT Input) for RAK entries?
    # Maybe they were posted there before?
    print("\n--- Checking Shared Account 40 for RAK entries ---")
    wrong_vat_lines = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id', '=', 40), ('company_id', '=', RAK_ID)]], {'context': ctx})
    print(f"Entries on Account 40 linked to RAK: {wrong_vat_lines}")

if __name__ == "__main__":
    debug_gl_entries()
