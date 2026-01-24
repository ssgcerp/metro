import xmlrpc.client

# Target Odoo 19
URL_19 = "https://metro.equdaierp.com"
DB_19 = "metrodb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

# Potential Source Odoo 14 (Localhost 8069)
URL_14 = "http://localhost:8069"
DB_14 = "metrodb" # Guessing
USER_14 = "admin"
PASS_14 = "Amaze@321"

def check_odoo19_fields():
    print(f"\n--- Checking Odoo 19 ({URL_19}) ---")
    try:
        common = xmlrpc.client.ServerProxy(f'{URL_19}/xmlrpc/2/common')
        uid = common.authenticate(DB_19, USER_19, PASS_19, {})
        models = xmlrpc.client.ServerProxy(f'{URL_19}/xmlrpc/2/object')
        
        fields = models.execute_kw(DB_19, uid, PASS_19, 'purchase.order', 'fields_get', [], {'attributes': ['string', 'type']})
        
        print("Searching for 'branch' or similar in Odoo 19 purchase.order:")
        for k, v in fields.items():
            if 'branch' in k.lower() or 'branch' in v.get('string', '').lower():
                print(f"FOUND: {k}: {v}")
                
    except Exception as e:
        print(f"Odoo 19 Error: {e}")

def check_odoo14_conn():
    print(f"\n--- Checking Odoo 14 ({URL_14}) ---")
    try:
        common = xmlrpc.client.ServerProxy(f'{URL_14}/xmlrpc/2/common')
        uid = common.authenticate(DB_14, USER_14, PASS_14, {})
        if uid:
            print(f"Connected to Odoo 14 as {uid}")
            # Check model
            models = xmlrpc.client.ServerProxy(f'{URL_14}/xmlrpc/2/object')
            fields = models.execute_kw(DB_14, uid, PASS_14, 'purchase.order', 'fields_get', [], {'attributes': ['string']})
            if 'branch_id' in fields:
                print("Confirmed 'branch_id' exists on Source.")
            else:
                print("'branch_id' NOT found on Source.")
        else:
            print("Auth failed.")
    except Exception as e:
        print(f"Odoo 14 Error: {e}")

def main():
    check_odoo19_fields()
    check_odoo14_conn()

if __name__ == "__main__":
    main()
