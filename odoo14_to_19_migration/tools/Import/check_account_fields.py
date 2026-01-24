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

        # Check account.account fields
        fields_acc = models.execute_kw(DB, uid, PASS, 'account.account', 'fields_get', [], {'attributes': ['string', 'type']})
        print("account.account fields (partial):")
        
        candidates = ['company_id', 'company_ids']
        for c in candidates:
             if c in fields_acc:
                 print(f"{c}: {fields_acc[c]}")
             else:
                 print(f"{c}: NOT FOUND")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
