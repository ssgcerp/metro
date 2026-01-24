import xmlrpc.client

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

PRODUCT_NAME = "FOOD EXPENSE"

def main():
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

        # Find Product
        prods = models.execute_kw(DB, uid, PASS, 'product.template', 'search', [[('name', '=', PRODUCT_NAME), ('can_be_expensed', '=', True)]])
        if not prods:
            print("Product not found")
            return
        prod_id = prods[0]
        print(f"Product ID: {prod_id}")

        # Get all companies
        companies = models.execute_kw(DB, uid, PASS, 'res.company', 'search_read', [[]], {'fields': ['id', 'name']})

        for company in companies:
            comp_id = company['id']
            res = models.execute_kw(DB, uid, PASS, 'product.template', 'read', [[prod_id], ['property_account_expense_id']], {'context': {'company_id': comp_id}})
            val = res[0]['property_account_expense_id']
            print(f"[{company['name']}] Expense Account: {val}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
