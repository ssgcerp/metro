import xmlrpc.client

# Source Credentials (Odoo 14/18)
URL = "https://metro-fire-system-llc.odoo.com"
DB = "metro-fire-system-llc"
USER = "sruthi@metrofiresystems.com"
PASS = "Sruthi@321"

def main():
    print(f"Connecting to {URL}...")
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASS, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        
        print("Connected. Inspecting purchase.order fields...")
        fields = models.execute_kw(DB, uid, PASS, 'purchase.order', 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
        
        # Look for "Branch"
        print("\nPossible Branch fields:")
        for field, props in fields.items():
            if 'branch' in field.lower() or 'branch' in props.get('string', '').lower():
                print(f"{field}: {props}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
