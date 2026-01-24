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

        # Check attributes
        fields = models.execute_kw(DB, uid, PASS, 'product.template', 'fields_get', 
            [['property_account_expense_id']], 
            {'attributes': ['string', 'type', 'company_dependent']})
        
        print(f"Fields: {fields}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
