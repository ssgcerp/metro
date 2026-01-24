import xmlrpc.client

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

TEST_CATEGORY = "FOOD EXPENSE"

def main():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

        # 1. Find ALL Products with the name
        product_ids = models.execute_kw(DB, uid, PASS, 'product.template', 'search', [[('name', '=', TEST_CATEGORY)]])
        if not product_ids:
            print(f"Product '{TEST_CATEGORY}' not found.")
            return

        print(f"Found {len(product_ids)} products named '{TEST_CATEGORY}': {product_ids}")

        # 2. Get all companies
        companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})

        for prod_id in product_ids:
            print(f"\n--- Checking Product ID: {prod_id} ---")
            # Get basic info
            info = models.execute_kw(DB, uid, PASS, 'product.template', 'read', [[prod_id], ['name', 'can_be_expensed', 'type']])
            print(f"Info: {info[0]}")
            
            # 3. Check property_account_expense_id for each company
            for company in companies:
                comp_id = company['id']
                val = models.execute_kw(DB, uid, PASS, 'product.template', 'read', [[prod_id], ['property_account_expense_id']], {'context': {'company_id': comp_id}})[0]['property_account_expense_id']
                if val:
                    print(f"  [{company['name']}] Expense Account: {val}")
                else:
                    # Only print if missing
                    # print(f"  [{company['name']}] Expense Account: False")
                    pass

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
