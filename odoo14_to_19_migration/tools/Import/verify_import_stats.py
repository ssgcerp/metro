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

        # 1. Investigate 'nan' product
        nan_prods = models.execute_kw(DB, uid, PASS, 'product.template', 'search_read', 
            [[('name', '=', 'nan')]], 
            {'fields': ['id', 'name', 'can_be_expensed', 'property_account_expense_id']})
        
        print("\n--- 'nan' Product Investigation ---")
        if nan_prods:
            print(f"Found {len(nan_prods)} products named 'nan':")
            for p in nan_prods:
                print(p)
        else:
            print("No 'nan' product found (maybe it was renamed?).")

        # 2. Count Total Expense Products
        # Assuming most were created today or have can_be_expensed=True
        # We can just count all expense products and see if it's close to 111 + originals
        count = models.execute_kw(DB, uid, PASS, 'product.template', 'search_count', [[('can_be_expensed', '=', True)]])
        print(f"\nTotal Expense Products: {count}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
