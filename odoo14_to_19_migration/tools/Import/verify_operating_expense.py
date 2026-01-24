import xmlrpc.client

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

TEST_CATEGORY = "OPERATING EXPENSE"

def main():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

        # 1. Find Product
        product_ids = models.execute_kw(DB, uid, PASS, 'product.template', 'search', [[('name', '=', TEST_CATEGORY), ('can_be_expensed', '=', True)]])
        if not product_ids:
            print(f"Product '{TEST_CATEGORY}' not found.")
            return
        prod_id = product_ids[0]
        print(f"Product: {TEST_CATEGORY} (ID: {prod_id})")

        # 2. Get all companies
        companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})

        # 3. Check property
        for company in companies:
            comp_id = company['id']
            val = models.execute_kw(DB, uid, PASS, 'product.template', 'read', [[prod_id], ['property_account_expense_id']], {'context': {'company_id': comp_id}})[0]['property_account_expense_id']
            print(f"[{company['name']}] Expense Account: {val}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
