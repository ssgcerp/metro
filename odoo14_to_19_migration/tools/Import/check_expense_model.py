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

        # Check hr.expense.category fields
        fields = models.execute_kw(DB, uid, PASS, 'hr.expense.category', 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
        print("hr.expense.category fields:")
        keys = sorted(fields.keys())
        for k in keys:
            print(f"{k}: {fields[k]}")

        print("\n-------------------\n")

        # Check account.account fields
        fields_acc = models.execute_kw(DB, uid, PASS, 'account.account', 'fields_get', [], {'attributes': ['string', 'type']})
        print("account.account fields (partial):")
        if 'code' in fields_acc: print(f"code: {fields_acc['code']}")
        if 'company_id' in fields_acc: print(f"company_id: {fields_acc['company_id']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
