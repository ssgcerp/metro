import xmlrpc.client

URL = "https://metro.equdaierp.com"
DB = "metrodb"
USER = "admin"
PASS = "Amaze@321"

PRODUCT_NAME = "FOOD EXPENSE"
# Hardcoded IDs from previous inspection
# Account 371 = L.FOOD EXPENSE (Code 123)
# Account 414 = Kitchen... (Code 400403)
TARGET_ACCOUNT_ID = 371 

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

        # Pick a Company (e.g. Ajman, ID 5)
        # Note: company_ids for Account 371 includes 5.
        COMP_ID = 5
        
        # Read before
        before = models.execute_kw(DB, uid, PASS, 'product.template', 'read', [[prod_id], ['property_account_expense_id']], {'context': {'company_id': COMP_ID}})
        print(f"Before Write [{COMP_ID}]: {before[0]['property_account_expense_id']}")
        
        # Write
        print(f"Writing Account {TARGET_ACCOUNT_ID}...")
        models.execute_kw(DB, uid, PASS, 'product.template', 'write', [[prod_id], {
            'property_account_expense_id': TARGET_ACCOUNT_ID
        }], {'context': {'company_id': COMP_ID}})
        
        # Read after
        after = models.execute_kw(DB, uid, PASS, 'product.template', 'read', [[prod_id], ['property_account_expense_id']], {'context': {'company_id': COMP_ID}})
        print(f"After Write [{COMP_ID}]: {after[0]['property_account_expense_id']}")

        # Check existing ir.property for this field/record
        # res_id string is "product.template,6893"
        res_id_str = f"product.template,{prod_id}"
        props = models.execute_kw(DB, uid, PASS, 'ir.property', 'search_read', 
            [[('name', '=', 'property_account_expense_id'), ('res_id', '=', res_id_str), ('company_id', '=', COMP_ID)]], 
            {'fields': ['value_reference', 'company_id']})
        print(f"Direct ir.property check: {props}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
