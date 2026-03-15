import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def move_vat_output():
    RAK_ID = 2
    ctx = {'allowed_company_ids': [1, RAK_ID]}
    
    NEW_OUTPUT_ID = 1761
    OLD_SALES_ID = 401100 # Code from previous output, but need ID...
    # Let's search for Account with code 401100 to get its ID
    sales_acc = models.execute_kw(db, uid, password, 'account.account', 'search_read',
        [[('code', '=', '401100'), ('company_ids', 'in', [RAK_ID])]],
        {'fields': ['id'], 'context': ctx})
        
    if not sales_acc:
        print("Sales account 401100 not found for RAK.")
        return
        
    SALES_ID = sales_acc[0]['id']
    print(f"Found Sales Account ID: {SALES_ID}")
    
    # Search for lines to move
    # Criteria: RAK company, Account = Sales, Name has 'VAT', Credit > 0
    lines_to_move = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
        [[('company_id', '=', RAK_ID), ('account_id', '=', SALES_ID), ('name', 'ilike', 'VAT'), ('credit', '>', 0)]],
        {'fields': ['id', 'name', 'credit'], 'context': ctx})
        
    print(f"Found {len(lines_to_move)} VAT Output lines on Sales Account.")
    
    if lines_to_move:
        ids_to_move = [l['id'] for l in lines_to_move]
        print(f"Moving {len(ids_to_move)} lines to VAT Output (ID {NEW_OUTPUT_ID})...")
        
        try:
             models.execute_kw(db, uid, password, 'account.move.line', 'write',
                [ids_to_move, {'account_id': NEW_OUTPUT_ID}],
                {'context': ctx})
             print("Success! Lines moved.")
        except Exception as e:
            print(f"Error moving lines: {e}")

if __name__ == "__main__":
    move_vat_output()
