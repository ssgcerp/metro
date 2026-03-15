import xmlrpc.client

url = "https://metro.equdaierp.com"
db = "metrodb" # User specified DB
username = "admin"
password = "Amaze@321"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
try:
    uid = common.authenticate(db, username, password, {})
    if uid:
        print(f"Successfully authenticated to '{db}' with UID: {uid}")
        
        # Check RAK accounts here
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        RAK_ID = 2 # Assuming ID 2 is still RAK, but should verify
        
        # Check RAK Company
        companies = models.execute_kw(db, uid, password, 'res.company', 'search_read',
            [[('name', 'ilike', 'RAS AL KHAIMAH')]], {'fields': ['id', 'name']})
        print(f"Companies matching RAK: {companies}")
        
        if companies:
            rak_real_id = companies[0]['id']
            # Check VAT Input
            vat_in = models.execute_kw(db, uid, password, 'account.account', 'search_read',
                [[('code', '=', '104041'), '|', ('company_ids', 'in', [rak_real_id]), ('company_ids', '=', False)]],
                {'fields': ['id', 'name', 'code', 'company_ids']})
            print(f"VAT Input (104041) for RAK: {vat_in}")
            
            # Check VAT Output
            vat_out = models.execute_kw(db, uid, password, 'account.account', 'search_read',
                [[('code', '=', '201017'), '|', ('company_ids', 'in', [rak_real_id]), ('company_ids', '=', False)]],
                {'fields': ['id', 'name', 'code', 'company_ids']})
            print(f"VAT Output (201017) for RAK: {vat_out}")
            
    else:
        print(f"Authentication failed for '{db}'.")
except Exception as e:
    print(f"Connection error: {e}")
