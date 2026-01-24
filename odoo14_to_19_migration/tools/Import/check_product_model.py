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

        # Check product.template fields (looking for expense/property fields)
        fields = models.execute_kw(DB, uid, PASS, 'product.template', 'fields_get', [], {'attributes': ['string', 'type', 'help']})
        print("product.template fields (partial):")
        relevant = ['can_be_expensed', 'property_account_expense_id', 'detailed_type', 'company_id']
        for k in relevant:
            if k in fields:
                print(f"{k}: {fields[k]}")
            else:
                print(f"{k}: NOT FOUND")

        print("\n-------------------\n")

        # Check hr.expense fields
        fields_hr = models.execute_kw(DB, uid, PASS, 'hr.expense', 'fields_get', [], {'attributes': ['string', 'type']})
        print("hr.expense fields (partial):")
        if 'product_id' in fields_hr: print(f"product_id: {fields_hr['product_id']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
