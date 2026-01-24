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
        
        print(f"Logged in as UID: {uid}")
        
        # Check installed modules
        print("\nChecking 'purchase' module state...")
        mods = models.execute_kw(DB, uid, PASS, 'ir.module.module', 'search_read', [[('name', '=', 'purchase')]], {'fields': ['state']})
        print(f"Purchase Module: {mods}")

        # Search for purchase models
        print("\nSearching for models like 'purchase'...")
        model_list = models.execute_kw(DB, uid, PASS, 'ir.model', 'search_read', [[('model', 'ilike', 'purchase')]], {'fields': ['model', 'name'], 'limit': 10})
        for m in model_list:
            print(f"{m['model']} ({m['name']})")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
