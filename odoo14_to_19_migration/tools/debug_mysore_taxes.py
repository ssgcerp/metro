import json
import random
import requests
import sys

# Configuration
URL = 'https://metro.equdaierp.com'
DB = 'metrodb'
# USER/PASS hardcoded for quick debug, usually bad practice but acceptable for one-off debug script in this context
USER = 'admin' 
PASSWORD = 'Amaze@321'

class OdooJsonRpcClient:
    def __init__(self, url, db, username, password):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.uid = None

    def json_rpc(self, endpoint, params):
        data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": random.randint(0, 1000000000),
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = self.session.post(f"{self.url}{endpoint}", data=json.dumps(data), headers=headers)
            return response.json()
        except Exception as e:
            print(f"RPC Error: {e}")
            return {}

    def authenticate(self):
        params = {"db": self.db, "login": self.username, "password": self.password}
        result = self.json_rpc("/web/session/authenticate", params)
        if result and 'result' in result and 'uid' in result['result']:
            self.uid = result['result']['uid']
            return True
        return False

    def execute_kw(self, model, method, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        params = {"model": model, "method": method, "args": args, "kwargs": kwargs}
        result = self.json_rpc("/web/dataset/call_kw", params)
        if result.get('error'):
            print(f"RPC Error ({method}): {result['error']}")
            return []
        return result.get('result')

def main():
    print("Connecting...")
    client = OdooJsonRpcClient(URL, DB, USER, PASSWORD)
    if not client.authenticate():
        print("Authentication Failed")
        return

    print("Authenticated.")

    # 1. Find Company 'mysore restaurant'
    print("Searching for 'mysore' company...")
    companies = client.execute_kw('res.company', 'search_read', 
        [[('name', 'ilike', 'mysore')]], 
        {'fields': ['id', 'name']})
    
    if not companies:
        print("Company 'mysore restaurant' not found.")
        return
    
    company = companies[0]
    company_id = company['id']
    print(f"Found Company: {company['name']} (ID: {company_id})")
    
    # Check Address for Emirate
    comp_data = client.execute_kw('res.company', 'read', [[company_id]], {'fields': ['state_id', 'city', 'street']})
    if comp_data:
        state = comp_data[0].get('state_id')
        print(f"Company Address: {comp_data[0].get('city')}, {comp_data[0].get('street')}, State: {state}")

    # List Key Tags
    print("\nSearch for VAT Tags (1...):")
    tags = client.execute_kw('account.account.tag', 'search_read', 
        [[('name', 'like', '1(%')]], 
        {'fields': ['name', 'id']})
    for t in tags:
        print(f"Tag: {t['name']} (ID: {t['id']})")
    
    # 2. Fetch Posted Customer Invoices in 2025
    domain = [
        ('move_type', '=', 'out_invoice'),
        ('company_id', '=', company_id),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', '2025-01-01'),
        ('invoice_date', '<=', '2025-12-31')
    ]
    
    print("Searching for posted invoices in 2025...")
    invoices = client.execute_kw('account.move', 'search_read', [domain], 
        {'fields': ['name', 'amount_total', 'amount_tax', 'invoice_line_ids'], 'limit': 5})

    if not invoices:
        print("No posted invoices found for 2025.")
        return

    print(f"Found {len(invoices)} sample invoices. checking details...")

    # 3. Analyze Tax Configuration on Invoice Lines
    for inv in invoices:
        print(f"\nInvoice: {inv['name']} | Total: {inv['amount_total']} | Tax: {inv['amount_tax']}")
        
        if not inv['invoice_line_ids']:
            print("  No invoice lines.")
            continue

        lines = client.execute_kw('account.move.line', 'read', [inv['invoice_line_ids']], 
            {'fields': ['name', 'price_unit', 'tax_ids', 'tax_tag_ids']})
        
        if not lines:
             print("  Could not read lines.")
             continue

        for line in lines:
            line_tax_ids = line.get('tax_ids', [])
            if not line_tax_ids:
                print(f"  - Line: {line['name']} | Price: {line['price_unit']} | NO TAXES APPLIED")
                continue
            
            print(f"  - Line: {line['name']} | Taxes: {line_tax_ids}")
            
            # Fetch Tax Names
            taxes = client.execute_kw('account.tax', 'read', [line_tax_ids], 
                {'fields': ['name', 'amount', 'invoice_repartition_line_ids', 'type_tax_use', 'country_id']})
            
            if not taxes:
                print("    -> Could not read tax details.")
                continue

            for tax in taxes:
                print(f"    -> Tax: {tax['name']} ({tax['amount']}%) Type: {tax['type_tax_use']} CountryID: {tax.get('country_id')}")
                
                # Check Repartition Lines (This controls Report Grids)
                rep_ids = tax.get('invoice_repartition_line_ids', [])
                if not rep_ids:
                    print(f"       !! WARNING: No repartition lines found for tax {tax['name']}")
                    continue

                repartition_lines = client.execute_kw('account.tax.repartition.line', 'read', 
                    [rep_ids], 
                    {'fields': ['repartition_type', 'factor_percent', 'account_id', 'tag_ids']})
                
                if not repartition_lines:
                     print("       -> No repartition line data returned.")
                
                has_grid = False
                for rep in repartition_lines:
                    # We are looking for 'tax' type repartition lines that have 'tag_ids' (Tax Grids)
                    if rep['repartition_type'] == 'tax':
                        tag_ids = rep.get('tag_ids', [])
                        print(f"       -> Repartition (Tax): Account={rep['account_id']}, Tags={tag_ids}")
                        
                        if tag_ids:
                            has_grid = True
                            tags = client.execute_kw('account.account.tag', 'read', [tag_ids], {'fields': ['name']})
                            if tags:
                                for t in tags:
                                    print(f"          -> Grid Tag: {t['name']}")
                
                if not has_grid:
                    print(f"       !! CRITICAL: Tax '{tax['name']}' has NO Tax Grids (Tags) linked! It won't show on the report.")

    # 4. Compare with a 'Good' Tax from Company 1 (likely 'Metro')
    print("\n--- Comparing with Standard UAE Tax (Company 1) ---")
    good_taxes = client.execute_kw('account.tax', 'search_read', 
        [[('company_id', '=', 1), ('type_tax_use', '=', 'sale'), ('amount', '=', 5.0)]], 
        {'fields': ['name', 'invoice_repartition_line_ids'], 'limit': 1})
    
    if good_taxes:
        gtax = good_taxes[0]
        print(f"Reference Tax: {gtax['name']}")
        rep_lines = client.execute_kw('account.tax.repartition.line', 'read', 
            [gtax['invoice_repartition_line_ids']], 
            {'fields': ['repartition_type', 'tag_ids']})
        
        for rep in rep_lines:
             if rep['repartition_type'] == 'tax':
                 tag_ids = rep.get('tag_ids', [])
                 if tag_ids:
                     tags = client.execute_kw('account.account.tag', 'read', [tag_ids], {'fields': ['name']})
                     tag_names = [t['name'] for t in tags]
                     print(f"  -> Good Tax Tags: {tag_names} (IDs: {tag_ids})")


if __name__ == "__main__":
    main()
