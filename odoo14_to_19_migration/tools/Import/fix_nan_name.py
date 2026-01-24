import xmlrpc.client

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

OLD_NAME = "nan"
NEW_NAME = "Others - Others" # Account Name is 'Others', and it seems to be an 'Others' category implicitly.

def main():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

        # Find Product
        prods = models.execute_kw(DB, uid, PASS, 'product.template', 'search', [[('name', '=', OLD_NAME)]])
        if not prods:
            print("Product 'nan' not found.")
            return
        
        prod_id = prods[0]
        print(f"Renaming Product ID {prod_id} from '{OLD_NAME}' to '{NEW_NAME}'...")
        
        models.execute_kw(DB, uid, PASS, 'product.template', 'write', [[prod_id], {
            'name': NEW_NAME
        }])
        
        print("Done.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
