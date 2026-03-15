import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb"
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def verify_balances():
    RAK_ID = 2
    ctx = {'allowed_company_ids': [1, RAK_ID]}
    
    vat_in_id = 1764
    vat_out_id = 1761
    
    print(f"--- Verifying RAK VAT Balances in {db} ---")
    
    # 1. Input
    # Count first
    lines_in = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id', '=', vat_in_id), ('company_id', '=', RAK_ID)]], {'context': ctx})

    # read_group(domain, fields, groupby)
    # Must pass as args list: [domain, fields, groupby]
    res_in = models.execute_kw(db, uid, password, 'account.move.line', 'read_group',
        [[('account_id', '=', vat_in_id), ('company_id', '=', RAK_ID)], ['debit', 'credit'], []],
        {'context': ctx})
        
    bal_in = 0
    if res_in and isinstance(res_in, list):
        bal_in = res_in[0]['debit'] - res_in[0]['credit']
    print(f"VAT Input (1764): {lines_in} entries | Balance: {bal_in}")

    # 2. Output
    lines_out = models.execute_kw(db, uid, password, 'account.move.line', 'search_count',
        [[('account_id', '=', vat_out_id), ('company_id', '=', RAK_ID)]], {'context': ctx})
        
    res_out = models.execute_kw(db, uid, password, 'account.move.line', 'read_group',
        [[('account_id', '=', vat_out_id), ('company_id', '=', RAK_ID)], ['debit', 'credit'], []],
        {'context': ctx})
        
    bal_out = 0
    if res_out and isinstance(res_out, list):
        bal_out = res_out[0]['debit'] - res_out[0]['credit']
    print(f"VAT Output (1761): {lines_out} entries | Balance: {bal_out}")

if __name__ == "__main__":
    verify_balances()
