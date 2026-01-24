import xmlrpc.client
import ssl
import sys

# Configure SSL context to ignore certificate verification if needed
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

class OdooClient:
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        self.uid = None

    def authenticate(self):
        try:
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            return bool(self.uid)
        except Exception as e:
            print(f"Authentication Failed for {self.url}: {e}")
            return False

    def search_read(self, model, domain, fields):
        return self.models.execute_kw(self.db, self.uid, self.password, model, 'search_read', [domain], {'fields': fields})

def main():
    print("="*60)
    print("COMPARING QUOTATIONS: ODOO 14 vs ODOO 19")
    print("="*60)

    # 1. Connect to Odoo 19
    # Using defaults from import_vendor_bills.py (likely the dev environment)
    o19_url = "https://metro.equdaierp.com"
    o19_db = "metrodb"
    o19_user = "admin" 
    o19_pass = "Amaze@321"

    print(f"\nConnecting to Odoo 19 ({o19_url})...")
    o19 = OdooClient(o19_url, o19_db, o19_user, o19_pass)
    if not o19.authenticate():
        print("FATAL: Could not connect to Odoo 19.")
        sys.exit(1)
    print("Connected.")

    # 2. Get Odoo 14 Configuration
    print("Retrieving Odoo 14 configuration...")
    configs = o19.search_read('odoo14.migration.config', [], ['odoo14_url', 'odoo14_database', 'odoo14_username', 'odoo14_password'])
    
    if not configs:
        print("FATAL: No 'odoo14.migration.config' record found in Odoo 19.")
        sys.exit(1)
    
    config = configs[0]
    o14_url = config['odoo14_url']
    o14_db = config['odoo14_database']
    o14_user = config['odoo14_username']
    o14_pass = config['odoo14_password']

    # 3. Connect to Odoo 14
    print(f"\nConnecting to Odoo 14 ({o14_url})...")
    o14 = OdooClient(o14_url, o14_db, o14_user, o14_pass)
    if not o14.authenticate():
        print("FATAL: Could not connect to Odoo 14 using stored credentials.")
        sys.exit(1)
    print("Connected.")

    # 4. Fetch Quotations/Orders
    # We want 'sale.order'. Note: Quotations are just SOs in 'draft' or 'sent' state, but usually we move everything?
    # The user said "list out quotations", implying numbers.
    # We should probably compare ALL sale.orders to be safe, or just quotations?
    # Usually in migration we want to ensure everything moved. 
    # Let's fetch ALL by default.
    
    print("\nFetching Odoo 14 Sale Orders...")
    # Fetch only 'name' to verify existence
    o14_orders = o14.search_read('sale.order', [], ['name'])
    o14_names = {r['name'] for r in o14_orders}
    print(f"Found {len(o14_names)} orders in Odoo 14.")

    print("Fetching Odoo 19 Sale Orders...")
    o19_orders = o19.search_read('sale.order', [], ['name'])
    o19_names = {r['name'] for r in o19_orders}
    print(f"Found {len(o19_names)} orders in Odoo 19.")

    # 5. Compare
    missing = o14_names - o19_names
    
    print("\n" + "="*60)
    print(f"MISSING QUOTATIONS ({len(missing)})")
    print("="*60)
    
    if missing:
        # Sort for readability
        for name in sorted(list(missing)):
            print(name)
        
        print("\nSummary:")
        print(f"Odoo 14 Total: {len(o14_names)}")
        print(f"Odoo 19 Total: {len(o19_names)}")
        print(f"Missing:       {len(missing)}")
    else:
        print("SUCCESS: All Odoo 14 quotations exist in Odoo 19!")

if __name__ == "__main__":
    main()
