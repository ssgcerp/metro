import xmlrpc.client

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

def main():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

        # Check product.template fields
        fields = models.execute_kw(DB, uid, PASS, 'product.template', 'fields_get', [], {'attributes': ['string', 'type', 'selection']})
        
        has_type = 'type' in fields
        has_detailed_type = 'detailed_type' in fields
        
        print(f"Has 'type': {has_type}")
        print(f"Has 'detailed_type': {has_detailed_type}")
        
        if has_type:
            print(f"Type selection: {fields['type'].get('selection')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
