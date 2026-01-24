import xmlrpc.client

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

PRODUCT_ID = 6893
PROPERTY_NAME = 'property_account_expense_id'

def main():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

        res_id_str = f"product.template,{PRODUCT_ID}"
        
        # Search all properties for this field and record
        props = models.execute_kw(DB, uid, PASS, 'ir.property', 'search_read', 
            [[('name', '=', PROPERTY_NAME), ('res_id', '=', res_id_str)]], 
            {'fields': ['company_id', 'value_reference', 'type']})
            
        print(f"Properties found for {res_id_str}:")
        for p in props:
            print(p)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
