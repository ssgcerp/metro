import xmlrpc.client
import time

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

PRODUCT_NAME = "FOOD EXPENSE"
TARGET_ACCOUNT_ID = 371 
COMP_ID = 5 # Ajman

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

        # Write
        print(f"Writing Account {TARGET_ACCOUNT_ID} for Company {COMP_ID}...")
        models.execute_kw(DB, uid, PASS, 'product.template', 'write', [[prod_id], {
            'property_account_expense_id': TARGET_ACCOUNT_ID
        }], {'context': {'company_id': COMP_ID}})
        
        # Read immediately
        res = models.execute_kw(DB, uid, PASS, 'product.template', 'read', [[prod_id], ['property_account_expense_id']], {'context': {'company_id': COMP_ID}})
        print(f"Immediate Read: {res[0]['property_account_expense_id']}")

        print("Waiting 5 seconds...")
        time.sleep(5)

        # Read again
        res = models.execute_kw(DB, uid, PASS, 'product.template', 'read', [[prod_id], ['property_account_expense_id']], {'context': {'company_id': COMP_ID}})
        print(f"Delayed Read: {res[0]['property_account_expense_id']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
